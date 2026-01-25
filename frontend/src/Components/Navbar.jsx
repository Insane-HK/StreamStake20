import React from 'react';
import { Zap } from 'lucide-react';
import { useWallet } from '../context/WalletContext'; // Import the hook

const Navbar = () => {
    // Destructure values from context
    const { walletConnected, walletId, connectWallet } = useWallet();

    return (
        <nav className="flex items-center justify-between px-10 py-6 border-b border-white/5 bg-[#0F1923]/95 backdrop-blur-xl sticky top-0 z-[60]">
            <div className="flex items-center gap-6">
                <div className="relative w-12 h-12 flex items-center justify-center">
                    <div className="absolute inset-0 bg-[#FF4655] transform skew-x-[-15deg] shadow-[4px_4px_0px_0px_#000]"></div>
                    <Zap className="relative z-10 text-white" size={24} fill="white" />
                </div>
                <div className="flex flex-col">
                    <span className="text-2xl font-black tracking-tighter italic uppercase leading-none">StreamStack</span>
                    <span className="text-[9px] font-mono tracking-[0.4em] text-[#FF4655] uppercase mt-1">Protocol: Radiant</span>
                </div>
            </div>

            <div className="flex items-center gap-8">
                <button
                    onClick={connectWallet}
                    disabled={walletConnected}
                    className={`px-8 py-2.5 border transition-all font-black uppercase text-[10px] tracking-[0.3em] relative overflow-hidden group cursor-pointer
                    ${walletConnected ? 'border-[#FF4655] text-[#FF4655] bg-[#FF4655]/5' : 'border-[#ECE8E1] bg-[#ECE8E1] text-[#0F1923] shadow-[4px_4px_0px_0px_#FF4655]'}`}
                >
                    <span className="relative z-10 transition-colors duration-0">
                        {walletConnected ? walletId : "Connect Wallet"}
                    </span>
                    {!walletConnected && (
                        <div className="absolute inset-0 bg-[#FF4655] translate-y-full group-hover:translate-y-0 transition-transform duration-300"></div>
                    )}
                </button>
            </div>
        </nav>
    );
};

export default Navbar;