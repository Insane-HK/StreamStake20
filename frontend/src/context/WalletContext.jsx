// src/context/WalletContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';

const WalletContext = createContext();

export const WalletProvider = ({ children }) => {
    const [walletConnected, setWalletConnected] = useState(false);
    const [walletId, setWalletId] = useState(""); // STORE FULL ADDRESS HERE
    const [error, setError] = useState("");

    const connectWallet = async () => {
        if (typeof window.ethereum !== 'undefined') {
            try {
                const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
                if (accounts.length > 0) {
                    // CHANGE: Store the raw, full address
                    setWalletId(accounts[0]);
                    setWalletConnected(true);
                    setError("");
                }
            } catch (err) {
                console.error(err);
                // ... error handling
            }
        } else {
            alert("MetaMask is not installed.");
        }
    };

    // ... disconnect logic ...

    useEffect(() => {
        if (typeof window.ethereum !== 'undefined') {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length > 0) {
                    // CHANGE: Store raw address on change too
                    setWalletId(accounts[0]);
                    setWalletConnected(true);
                } else {
                    setWalletConnected(false);
                    setWalletId("");
                }
            });
        }
    }, []);

    return (
        <WalletContext.Provider value={{ walletConnected, walletId, connectWallet, error }}>
            {children}
        </WalletContext.Provider>
    );
};

export const useWallet = () => {
    const context = useContext(WalletContext);
    if (!context) throw new Error('useWallet must be used within a WalletProvider');
    return context;
};