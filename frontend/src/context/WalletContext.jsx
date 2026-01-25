import React, { createContext, useContext, useState, useEffect } from 'react';

const WalletContext = createContext();

// 1. Export the Provider
export const WalletProvider = ({ children }) => {
    const [walletConnected, setWalletConnected] = useState(false);
    const [walletId, setWalletId] = useState("");
    const [error, setError] = useState("");

    // Helper: Format the address to look nice (0x123...abc)
    const formatAddress = (addr) => {
        return `${addr.substring(0, 5)}...${addr.substring(addr.length - 4)}`;
    };

    const connectWallet = async () => {
        // Check if Ethereum provider (MetaMask) is injected
        if (typeof window.ethereum !== 'undefined') {
            try {
                // Request access to the user's accounts
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });

                if (accounts.length > 0) {
                    setWalletId(formatAddress(accounts[0]));
                    setWalletConnected(true);
                    setError("");
                }
            } catch (err) {
                console.error(err);
                if (err.code === 4001) {
                    alert("Connection rejected. Please approve the request in MetaMask.");
                } else {
                    alert("Error connecting wallet. Check console for details.");
                }
            }
        } else {
            alert("MetaMask (or a Web3 wallet) is not installed. Please install it to proceed.");
        }
    };

    const disconnectWallet = () => {
        // Note: You cannot fully disconnect MetaMask via code (only the user can do that in the extension).
        // We only clear the state in our app.
        setWalletConnected(false);
        setWalletId("");
    };

    // Optional: Auto-detect if user changes accounts in MetaMask
    useEffect(() => {
        if (typeof window.ethereum !== 'undefined') {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length > 0) {
                    setWalletId(formatAddress(accounts[0]));
                    setWalletConnected(true);
                } else {
                    // User disconnected via MetaMask interface
                    setWalletConnected(false);
                    setWalletId("");
                }
            });
        }
    }, []);

    return (
        <WalletContext.Provider value={{ walletConnected, walletId, connectWallet, disconnectWallet, error }}>
            {children}
        </WalletContext.Provider>
    );
};

// 2. Export the Hook
export const useWallet = () => {
    const context = useContext(WalletContext);
    if (!context) {
        throw new Error('useWallet must be used within a WalletProvider');
    }
    return context;
};