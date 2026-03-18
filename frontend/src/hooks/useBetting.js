import { useState } from 'react';
import { ethers } from 'ethers';
import { useWallet } from '../context/WalletContext';
import { TOKEN_ADDRESS, VAULT_ADDRESS, ERC20_ABI, VAULT_ABI } from '../config/contracts';
// We use Realtime Database to "Talk" to the bot
import { rtdb } from '../firebase';
import { ref, push, set, onValue, off, remove } from "firebase/database";

export const useBetting = () => {
    const { walletId } = useWallet();
    const [loading, setLoading] = useState(false);

    // Helper to get Contract Instances
    const getContracts = async () => {
        if (!window.ethereum) throw new Error("No Wallet Found");

        const provider = new ethers.BrowserProvider(window.ethereum);

        // 1. CHECK NETWORK
        const network = await provider.getNetwork();
        console.log(`🌍 Connected to Chain ID: ${network.chainId}`);
        if (Number(network.chainId) !== 10143) {
            alert(`Wrong Network! You are on Chain ${network.chainId}. Please switch to Monad Testnet (10143).`);
            return null;
        }

        // 2. CHECK IF CONTRACT EXISTS
        const code = await provider.getCode(TOKEN_ADDRESS);
        if (code === "0x") {
            console.error(`❌ No Contract found at ${TOKEN_ADDRESS}`);
            alert(`CRITICAL ERROR: No contract found at ${TOKEN_ADDRESS}. Did you redeploy and forget to update contracts.js?`);
            return null;
        }

        const signer = await provider.getSigner();
        const token = new ethers.Contract(TOKEN_ADDRESS, ERC20_ABI, signer);
        const vault = new ethers.Contract(VAULT_ADDRESS, VAULT_ABI, signer);
        return { token, vault };
    };

    // =========================================================
    // 1. DEPOSIT (Frontend -> Blockchain)
    // =========================================================
    const depositFunds = async (amountStr) => {
        setLoading(true);
        try {
            const { token, vault } = await getContracts();
            const weiAmount = ethers.parseUnits(amountStr.toString(), 18);

            // A1. Check Token Balance
            const balance = await token.balanceOf(walletId);
            if (balance < weiAmount) {
                alert(`Insufficient Balance! You have ${ethers.formatUnits(balance, 18)} tokens but are trying to deposit ${amountStr}.`);
                return false;
            }

            // A2. Check Allowance
            const allowance = await token.allowance(walletId, VAULT_ADDRESS);
            if (allowance < weiAmount) {
                console.log("Requesting Approval...");
                const txApprove = await token.approve(VAULT_ADDRESS, ethers.MaxUint256);
                await txApprove.wait();
            }

            // B. Deposit Transaction
            console.log("Sending Deposit TX...");
            const txDeposit = await vault.deposit(weiAmount);
            await txDeposit.wait();

            // The Bot will detect this event and update Firebase automatically.
            console.log("Deposit Confirmed on Blockchain. Waiting for Bot...");
            return true;

        } catch (error) {
            console.error("Deposit Failed:", error);
            alert(error.message);
            return false;
        } finally {
            setLoading(false);
        }
    };

    // =========================================================
    // 2. WITHDRAW (Frontend -> Firebase -> Bot -> Blockchain)
    // =========================================================
    const withdrawFunds = async (amountPoints) => {
        setLoading(true);
        try {
            if (amountPoints <= 0) throw new Error("Invalid amount");

            // A. Request Signature from Bot (Write to DB)
            console.log("Requesting signature from Bot...");
            const requestRef = push(ref(rtdb, "withdraw_requests"));
            const requestId = requestRef.key;

            await set(requestRef, {
                user: walletId,
                amount: parseFloat(amountPoints),
                status: "pending",
                timestamp: Date.now()
            });

            // B. Wait for Bot Response (Listen to DB)
            const signatureData = await new Promise((resolve, reject) => {
                const responseRef = ref(rtdb, `withdraw_responses/${walletId}`);

                // Timeout after 30 seconds
                const timeout = setTimeout(() => {
                    off(responseRef);
                    reject(new Error("Bot timed out. Is backend running?"));
                }, 30000);

                const listener = onValue(responseRef, (snapshot) => {
                    const data = snapshot.val();
                    // Check if this response matches our request (by ID or fresh timestamp)
                    if (data && data.requestId === requestId) {
                        clearTimeout(timeout);
                        off(responseRef, listener); // Stop listening
                        remove(responseRef); // Clean up DB
                        resolve(data);
                    }
                });
            });

            console.log("Bot Signature Received!", signatureData);

            // C. Submit Withdrawal to Blockchain
            const { vault } = await getContracts();
            const txWithdraw = await vault.withdraw(
                signatureData.amount,
                signatureData.nonce,
                signatureData.signature
            );

            console.log("Withdrawal TX sent:", txWithdraw.hash);
            await txWithdraw.wait();

            return true;

        } catch (error) {
            console.error("Withdraw Failed:", error);
            alert(error.message);
            return false;
        } finally {
            setLoading(false);
        }
    };

    return { depositFunds, withdrawFunds, loading };
};