# StreamStake20 Project Report

## 1. Overview
**StreamStake20** is an innovative Web3 betting platform that integrates real-time optical character recognition (OCR) with live gaming streams. Designed for competitive games like Valorant, CS2, and League of Legends, the platform enables viewers to place stakes on live matches. By bridging off-chain game state analysis with on-chain settlement, StreamStake20 offers a seamless, decentralized, and engaging betting experience for gaming enthusiasts.

## 2. System Architecture
The system consists of four primary components working in tandem to deliver real-time betting capabilities:

1. **Frontend Application**: A responsive, real-time user interface serving as the main touchpoint for users to watch streams, view live game states, and place bets.
2. **OCR Service (The Vision Engine)**: A sophisticated background service that monitors video feeds or screen captures, using machine learning to parse the game state and identify key phases (e.g., Betting Open, Locked, Result).
3. **Backend Oracle Bot**: A Node.js service connecting the off-chain game state (Firebase) with the on-chain settlement layer (Smart Contracts). It acts as the source of truth for match outcomes and processes financial logic.
4. **Smart Contracts**: The decentralized financial layer that handles reliable staking, payout distributions, and user fund management via web3 wallets.

## 3. Technologies Used
- **Frontend**: React (Vite), Tailwind CSS, React Player, Ethers.js
- **Backend / Oracle**: Node.js, Firebase Admin SDK, Ethers.js
- **Computer Vision & OCR**: Python, OpenCV, Tesseract OCR, `mss` (for rapid screen capturing)
- **Database & Real-time Sync**: Firebase Realtime Database
- **Blockchain**: Solidity, Monad Testnet

## 4. Key Components Deep-Dive

### 4.1. OCR Service
The OCR component captures the gaming display at a frequency of ~2Hz. It performs image processing localized to specific regions of interest (scaled automatically for 720p, 1080p, or 1440p) to extract current scores and game phase information. Upon detecting a transition—such as a round starting (BETTING phase) or ending (RESULT phase)—it immediately pushes this state to the Firebase Realtime Database, enabling sub-second synchronization with the frontend.

### 4.2. Backend Bot
Functioning as a custom Oracle, the Node.js bot continuously monitors both on-chain and off-chain states:
- **Deposit/Withdrawal Handling**: Watches the on-chain Vault contract for user deposits, reflecting these balances instantly in Firebase. For withdrawals, it listens to Firebase requests, validates balances, and securely signs EIP-712 messages to authorize on-chain fund retrieval.
- **Bet Settlement**: Listens for the `RESULT` phase triggered by the OCR service. Upon detecting a round conclusion, it automatically evaluates all active bets for the match, calculating and distributing payouts (e.g., 2x profit) directly to the winners' Firebase balances.

### 4.3. Smart Contracts
Deployed on the highly scalable Monad Testnet, the smart contracts ensure robust and transparent handling of funds:
- **Vault Contract**: Secures user deposits and validates cryptographic signatures parsed from the Backend Bot for withdrawals.
- **Betting Contracts**: Implements on-chain logic (`ValorantBetting.sol`) with built-in protections against reentrancy and manipulation, allowing users to place transparent stakes on specific team outcomes.

### 4.4. Frontend
A modern React-based Single Page Application (SPA) offering dedicated views:
- **Home/Lobby**: Displays available active streams and games.
- **Room Interface**: Embeds live streams via `react-player` and seamlessly overlays interactive betting UI elements. It relies on Firebase real-time listeners to instantly lock betting interfaces or highlight winners the moment the OCR service detects a screen change.

## 5. Security & Flow
1. **State Independence**: The OCR isolates game analysis from the client, preventing any user-side manipulation of the game outcome.
2. **Oracle Validation**: All financial processing and database updates run exclusively through the authenticated Backend Bot, guarding against malicious Firebase writes from clients.
3. **Smart Contract Security**: Includes standard OpenZeppelin guards (`ReentrancyGuard`, `Ownable`) and relies on EIP-712 signatures to prevent funds from being drained maliciously.

## 6. Future Enhancements
- **Multi-Game Expansion**: Easy integration of more competitive games by adding new templates and ROI coordinates to the OCR configuration.
- **Fully Decentralized Oracle Model**: Transitioning the centralized backend bot to a decentralized oracle network (e.g., Chainlink) for verifying OCR results via a consensus mechanism.
- **Advanced Betting Options**: Introducing micro-bets (e.g., "First Blood" or specific player kills) by fine-tuning the OCR to read the kill feed continuously.
