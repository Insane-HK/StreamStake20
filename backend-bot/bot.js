require('dotenv').config();
const admin = require("firebase-admin");
const { ethers } = require("ethers");

// ==================================================================
// 1. CONFIGURATION & SETUP
// ==================================================================
const firebasePrivateKey = process.env.FIREBASE_PRIVATE_KEY
    ? process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n')
    : undefined;

if (!firebasePrivateKey || !process.env.FIREBASE_PROJECT_ID || !process.env.FIREBASE_CLIENT_EMAIL) {
    console.error("❌ Missing Firebase credentials in .env file");
    process.exit(1);
}

admin.initializeApp({
    credential: admin.credential.cert({
        projectId: process.env.FIREBASE_PROJECT_ID,
        privateKey: firebasePrivateKey,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
    }),
    databaseURL: process.env.FIREBASE_DATABASE_URL
});

const db = admin.database();

const RPC_URL = process.env.RPC_URL || "https://testnet-rpc.monad.xyz/";
const VAULT_ADDRESS = process.env.VAULT_ADDRESS;
const PRIVATE_KEY = process.env.PRIVATE_KEY;

if (!VAULT_ADDRESS || !PRIVATE_KEY) {
    console.error("❌ Missing Blockchain credentials in .env file");
    process.exit(1);
}

const provider = new ethers.JsonRpcProvider(RPC_URL);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

const VAULT_ABI = ["event Deposit(address indexed user, uint256 amount)"];
const vaultContract = new ethers.Contract(VAULT_ADDRESS, VAULT_ABI, provider);

console.log("\n🤖 StreamStack Oracle Bot is Starting...");
console.log(`🌍 Network: Monad Testnet`);
console.log(`🏦 Vault:   ${VAULT_ADDRESS}`);
console.log("--------------------------------------------------\n");

// ==================================================================
// 2. WATCHER: DEPOSITS
// ==================================================================
let lastProcessedBlock = 0;

async function pollForDeposits() {
    try {
        const currentBlock = await provider.getBlockNumber();
        // Initialize on first run
        if (lastProcessedBlock === 0) {
            lastProcessedBlock = currentBlock - 1;
            console.log(`⚙️  Deposit Poller initialized at block: ${currentBlock}`);
            return;
        }

        if (currentBlock > lastProcessedBlock) {
            // Query logs from last seen block to current block
            const events = await vaultContract.queryFilter("Deposit", lastProcessedBlock + 1, currentBlock);
            for (const event of events) {
                const { user, amount } = event.args;
                const txHash = event.transactionHash;
                console.log(`💰 New Deposit: ${user} | ${ethers.formatUnits(amount, 18)}`);
                await processDeposit(user, amount, txHash);
            }
            lastProcessedBlock = currentBlock;
        }
    } catch (err) {
        console.error("⚠️  Polling Error:", err.message);
    }
}

async function processDeposit(user, amount, txHash) {
    try {
        // FIX: Force Lowercase Address
        const normalizedUser = user.toLowerCase();

        const txRef = db.ref(`transactions/${txHash}`);
        const txSnap = await txRef.once('value');
        if (txSnap.exists()) {
            console.log("   -> Tx already processed. Skipping.");
            return;
        }

        const pointsToAdd = parseFloat(ethers.formatUnits(amount, 18));

        // Update balance using normalized address
        await db.ref(`users/${normalizedUser}/balance`).transaction((current) => {
            return (current || 0) + pointsToAdd;
        });

        await txRef.set({
            user: normalizedUser,
            amount: pointsToAdd,
            timestamp: Date.now(),
            status: "confirmed",
            network: "monad-testnet"
        });

        console.log(`   ✅ Credited ${pointsToAdd} pts to ${normalizedUser}`);
    } catch (err) {
        console.error("   ❌ Error writing to Firebase:", err);
    }
}

// Poll every 3 seconds
setInterval(pollForDeposits, 10000);

// ==================================================================
// 3. WATCHER: WITHDRAWALS
// ==================================================================
const withdrawQueueRef = db.ref("withdraw_requests");

withdrawQueueRef.on("child_added", async (snapshot) => {
    const request = snapshot.val();
    const requestId = snapshot.key;

    if (request.status !== "pending") return;

    console.log(`📤 Processing Withdraw Request: ${request.user} (${request.amount} pts)`);

    try {
        // FIX: Force Lowercase Address
        const userAddress = request.user.toLowerCase();
        const amountPoints = request.amount;

        // Check Real Balance
        const userBalRef = db.ref(`users/${userAddress}/balance`);
        const userBalSnap = await userBalRef.once('value');
        const currentBal = userBalSnap.val() || 0;

        if (currentBal < amountPoints) {
            console.error("   ❌ Insufficient funds.");
            await snapshot.ref.update({ status: "rejected" });
            return;
        }

        const nonce = Date.now();
        const amountWei = ethers.parseUnits(amountPoints.toString(), 18);

        const messageHash = ethers.solidityPackedKeccak256(
            ["address", "uint256", "uint256", "address"],
            [userAddress, amountWei, nonce, VAULT_ADDRESS]
        );
        const signature = await wallet.signMessage(ethers.getBytes(messageHash));

        // Deduct Balance
        await userBalRef.set(currentBal - amountPoints);

        // Send Signature
        await db.ref(`withdraw_responses/${userAddress}`).set({
            signature, amount: amountWei.toString(), nonce, timestamp: Date.now()
        });

        await snapshot.ref.remove();
        console.log(`   ✅ Signature sent.`);
    } catch (err) {
        console.error("   ❌ Withdraw Error:", err);
    }
});

// ==================================================================
// 4. WATCHER: GAME SETTLEMENT
// ==================================================================
const lobbiesRef = db.ref("lobbies");

lobbiesRef.on("child_changed", async (snapshot) => {
    const lobbyId = snapshot.key;
    const lobbyData = snapshot.val();

    // Get Active Round
    if (!lobbyData.active_round) return;
    const roundId = lobbyData.active_round;

    const roundRef = db.ref(`lobbies/${lobbyId}/rounds/${roundId}`);
    const roundSnap = await roundRef.once('value');
    const round = roundSnap.val();

    if (!round) return;

    // Trigger on "RESULT" phase (Matches Python Backend)
    if (round.phase === "RESULT" && round.winner && !round.payout_processed) {
        console.log(`🏁 Round ${roundId} Ended! Winner: ${round.winner}`);

        try {
            // Lock round
            await roundRef.update({ payout_processed: true });

            const betsRef = db.ref(`bets/${lobbyId}`);
            const betsSnap = await betsRef.once('value');
            const bets = betsSnap.val();

            if (!bets) {
                console.log("   -> No bets found.");
                return;
            }

            let winnerCount = 0;
            const updates = {};

            for (const [betId, bet] of Object.entries(bets)) {
                if (bet.processed) continue;

                updates[`bets/${lobbyId}/${betId}/processed`] = true;

                if (bet.outcome === round.winner) {
                    const profit = bet.amount * 2;
                    winnerCount++;

                    // FIX: Force Lowercase Address for Payouts
                    const normalizedUser = bet.user.toLowerCase();

                    await db.ref(`users/${normalizedUser}/balance`).transaction((current) => (current || 0) + profit);
                    console.log(`   🎉 Paid ${normalizedUser}: ${profit} pts`);
                }
            }

            if (Object.keys(updates).length > 0) {
                await db.ref().update(updates);
            }
            console.log(`   ✅ Paid ${winnerCount} winners.`);

        } catch (err) {
            console.error("   ❌ Settlement Error:", err);
        }
    }
});