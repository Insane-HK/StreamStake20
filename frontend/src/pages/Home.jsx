import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Play, Activity, Target, Award, Trophy, Lock, X, Plus } from 'lucide-react';
import { useWallet } from '../context/WalletContext'; // Import the hook
import { rtdb } from '../firebase';
import { ref, set, get } from "firebase/database";

const COLORS = {
    vRed: '#FF4655',
    vNavy: '#0F1923',
    vWhite: '#ECE8E1',
    vGray: '#8B978F',
    vBlack: '#02070D',
};

// Removed props, using hook instead
const Home = () => {
    const navigate = useNavigate();
    const { walletConnected, connectWallet, walletId } = useWallet(); // Access global state
    const [showConnectModal, setShowConnectModal] = useState(false);

    // Lobby Creation State
    const [streamUrl, setStreamUrl] = useState('');
    const [isCreating, setIsCreating] = useState(false);

    // Join Lobby State
    const [joinLobbyId, setJoinLobbyId] = useState('');

    const handleJoinLobby = async () => {
        if (!joinLobbyId.trim()) return;

        try {
            const snapshot = await get(ref(rtdb, `lobbies/${joinLobbyId.toUpperCase()}`));
            if (snapshot.exists()) {
                const data = snapshot.val();
                const urlParam = data.streamUrl ? `?url=${encodeURIComponent(data.streamUrl)}` : '';
                navigate(`/room/${joinLobbyId.toUpperCase()}${urlParam}`);
            } else {
                alert("Lobby not found. Please check the ID.");
            }
        } catch (error) {
            console.error("Error joining lobby:", error);
            alert("Error joining lobby. Check console.");
        }
    };

    const handleCreateLobby = async () => {
        if (!streamUrl.trim()) return;

        setIsCreating(true);
        // Generate Random Lobby ID (4 chars)
        const lobbyId = Math.random().toString(36).substring(2, 6).toUpperCase();

        try {
            // Write to Firebase
            await set(ref(rtdb, `lobbies/${lobbyId}`), {
                streamUrl: streamUrl,
                createdAt: Date.now(),
                host: walletId || 'Guest',
                active_round: null
            });

            // Navigate to Room
            navigate(`/room/${lobbyId}?url=${encodeURIComponent(streamUrl)}`);
        } catch (error) {
            console.error("Failed to create lobby:", error);
            alert("Failed to create lobby. Check console.");
        } finally {
            setIsCreating(false);
        }
    };

    const handleStartPrediction = () => {
        if (!walletConnected) {
            setShowConnectModal(true);
            return;
        }
        navigate('/prediction');
    };

    const handleConnectAndClose = () => {
        connectWallet();
        setShowConnectModal(false);
    };

    return (
        <div className="min-h-screen font-sans bg-[#0F1923] text-[#ECE8E1] selection:bg-[#FF4655] selection:text-white overflow-x-hidden">

            {/* BACKGROUND DECOR */}
            <div className="fixed inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -left-20 top-1/2 -translate-y-1/2 opacity-5 select-none pointer-events-none flex items-center gap-4 origin-center -rotate-90">
                    <span className="text-[160px] font-black tracking-[0.2em] uppercase italic leading-none">VALORANT</span>
                </div>
                <div className="absolute inset-0 opacity-[0.08]" style={{ backgroundImage: 'radial-gradient(#FF4655 1px, transparent 1px)', backgroundSize: '40px 40px' }}></div>
                <div className="absolute top-[-20%] right-[-10%] w-[70%] h-[70%] bg-[#FF4655] blur-[250px] opacity-[0.07] rounded-full"></div>
            </div>

            {/* HERO SECTION */}
            <section className="px-10 pt-20 pb-32">
                <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-16 items-center">

                    <div className="relative">
                        <div className="flex flex-col gap-3 mb-8">
                            {/* NEW: Hackathon Winner Badge */}
                            <a 
                                href="https://dorahacks.io/hackathon/lnmhacks8/buidl"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-3 px-4 py-2 bg-[#FFD700]/10 border border-[#FFD700]/30 hover:bg-[#FFD700]/20 transition-all rounded-sm self-start group cursor-pointer"
                            >
                                <span className="text-[#FFD700]"><Trophy size={16} className="group-hover:scale-110 transition-transform" /></span>
                                <span className="text-[11px] font-black uppercase tracking-[0.3em] text-[#FFD700]">3rd Place Winner @ LNMHacks 8.0</span>
                            </a>

                            <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-[#FF4655]/10 border-l-2 border-[#FF4655] self-start">
                                <span className="text-[10px] font-black uppercase tracking-[0.4em] text-[#FF4655]">Analyzing Match Point</span>
                            </div>
                        </div>

                        <h1 className="font-black uppercase italic leading-[0.85] mb-8 text-7xl lg:text-9xl tracking-tight">
                            Win the <br />
                            <span className="text-transparent" style={{ WebkitTextStroke: `2px ${COLORS.vWhite}` }}>Clutch.</span>
                        </h1>

                        <div className="mb-12 space-y-4">
                            <p className="text-[#ECE8E1] text-2xl font-black italic uppercase leading-tight tracking-tight">
                                Master the prediction meta.
                            </p>
                            <p className="text-[#8B978F] text-lg max-w-lg font-medium leading-relaxed border-l border-white/10 pl-6">
                                Read the lineup before the dart lands. Join the elite network of Radiant-tier analysts predicting every site-take and round-clutch in real-time.
                            </p>
                        </div>

                        <div className="flex flex-col gap-6 w-full max-w-lg">
                            {/* CREATE LOBBY FORM */}
                            <div className="bg-white/5 p-6 border border-white/10 backdrop-blur-sm">
                                <h3 className="text-sm font-black uppercase tracking-[0.2em] text-[#8B978F] mb-4">Initialize Protocol</h3>
                                <div className="flex flex-col gap-4">
                                    <input
                                        type="text"
                                        placeholder="PASTE YOUTUBE URL..."
                                        value={streamUrl}
                                        onChange={(e) => setStreamUrl(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 px-4 py-3 text-sm font-mono text-white focus:border-[#FF4655] outline-none placeholder-white/20"
                                    />
                                    <button
                                        onClick={handleCreateLobby}
                                        disabled={isCreating || !streamUrl}
                                        className={`relative h-14 w-full bg-[#FF4655] text-white font-black uppercase tracking-[0.2em] text-lg transition-all duration-0 hover:bg-[#D93444] disabled:opacity-50 disabled:cursor-not-allowed`}
                                    >
                                        <span className="flex items-center justify-center gap-2">
                                            {isCreating ? <Activity className="animate-spin" size={20} /> : <Plus size={20} />}
                                            <span>Create Lobby</span>
                                        </span>
                                    </button>
                                </div>
                            </div>

                            {/* DEMO MODE BUTTON */}
                            <div className="mt-4">
                                <button
                                    onClick={() => navigate('/room/DEMO?url=https://www.youtube.com/watch?v=e_E9W2vsRbQ&alias=Recruiter')}
                                    className="relative h-14 w-full bg-transparent border-2 border-white text-white font-black uppercase tracking-[0.2em] text-lg transition-all duration-0 hover:bg-white hover:text-black overflow-hidden group"
                                >
                                    <div className="absolute inset-0 bg-white translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-in-out"></div>
                                    <span className="relative z-10 flex items-center justify-center gap-2">
                                        <Play size={20} />
                                        <span>Showcase Demo Mode</span>
                                    </span>
                                </button>
                                <p className="text-[10px] text-center text-[#8B978F] mt-2 font-mono uppercase tracking-widest">No Backend Required • Simulated Live Match</p>
                            </div>

                            {/* JOIN LOBBY FORM */}
                            <div className="bg-white/5 p-6 border border-white/10 backdrop-blur-sm">
                                <h3 className="text-sm font-black uppercase tracking-[0.2em] text-[#8B978F] mb-4">Join Operation</h3>
                                <div className="flex flex-col gap-4">
                                    <input
                                        type="text"
                                        placeholder="ENTER LOBBY ID..."
                                        value={joinLobbyId}
                                        onChange={(e) => setJoinLobbyId(e.target.value)}
                                        className="w-full bg-black/40 border border-white/10 px-4 py-3 text-sm font-mono text-white focus:border-[#22D3EE] outline-none placeholder-white/20"
                                        maxLength={6}
                                    />
                                    <button
                                        onClick={handleJoinLobby}
                                        disabled={!joinLobbyId}
                                        className={`relative h-14 w-full bg-[#22D3EE] text-black font-black uppercase tracking-[0.2em] text-lg transition-all duration-0 hover:bg-[#1BA8BE] disabled:opacity-50 disabled:cursor-not-allowed`}
                                        style={{ clipPath: 'polygon(0 0, 100% 0, 100% 100%, 10px 100%, 0 calc(100% - 10px))' }}
                                    >
                                        <span className="flex items-center justify-center gap-2">
                                            <Target size={20} />
                                            <span>Join Lobby</span>
                                        </span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* TERMINAL UI */}
                    <div className="relative group perspective-1000">
                        <div className="absolute -top-4 -left-4 w-12 h-12 border-t-2 border-l-2 border-[#FF4655] group-hover:-translate-x-2 group-hover:-translate-y-2 transition-transform"></div>
                        <div className="absolute -bottom-4 -right-4 w-12 h-12 border-b-2 border-r-2 border-[#FF4655] group-hover:translate-x-2 group-hover:translate-y-2 transition-transform"></div>

                        <div className="bg-[#0F1923] border border-white/10 p-8 shadow-[15px_15px_0px_0px_rgba(255,70,85,0.1)] rounded-sm relative z-10 transition-all duration-500 group-hover:shadow-[25px_25px_0px_0px_rgba(255,70,85,0.2)] group-hover:-translate-y-2 group-hover:-translate-x-2">
                            <div className="flex items-center justify-between mb-8">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-1 bg-[#FF4655]" />
                                    <span className="text-[10px] font-mono font-black text-[#FF4655] tracking-[0.4em] uppercase">Status: 5-6</span>
                                </div>
                                <Activity size={16} className="text-[#8B978F] animate-pulse" />
                            </div>

                            <div className="space-y-4 font-mono text-sm">
                                <div className="flex justify-between items-center text-[#ECE8E1] bg-white/5 p-4 border-l-2 border-[#FF4655]">
                                    <span className="font-bold flex items-center gap-2">ANALYZING_LIVE_HUD</span>
                                    <span className="text-[#FF4655] text-xs font-black uppercase">Active</span>
                                </div>
                                <div className="grid grid-cols-1 gap-1 text-[11px] p-4 text-[#8B978F] italic bg-black/20">
                                    <p>{'>'} DETECTING: TENZ (JETT)</p>
                                    <p className="text-cyan-400">{'>'} ULTIMATE: READY</p>
                                    <p className="text-green-400">{'>'} PREDICTION: 1v3 CLUTCH CHANCE</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div >
            </section >

            {/* WALLET CONNECT MODAL */}
            {
                showConnectModal && (
                    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowConnectModal(false)}></div>

                        <div className="relative w-full max-w-md bg-[#0F1923] border border-[#FF4655] p-8 shadow-[0_0_50px_rgba(255,70,85,0.2)] animate-[fadeIn_0.2s_ease-out]">
                            <button
                                onClick={() => setShowConnectModal(false)}
                                className="absolute top-4 right-4 text-[#8B978F] hover:text-white transition-colors"
                            >
                                <X size={20} />
                            </button>

                            <div className="flex flex-col items-center text-center">
                                <div className="w-16 h-16 rounded-full bg-[#FF4655]/10 flex items-center justify-center mb-6 border border-[#FF4655]/20">
                                    <Lock size={32} className="text-[#FF4655]" />
                                </div>

                                <h3 className="text-3xl font-black italic uppercase tracking-tighter mb-4">
                                    Access Denied
                                </h3>

                                <p className="text-[#8B978F] mb-8 leading-relaxed font-medium">
                                    Prediction terminal requires a verified cryptographic signature. Please connect your wallet to access the live analysis feed.
                                </p>

                                <button
                                    onClick={handleConnectAndClose}
                                    className="w-full py-4 bg-[#FF4655] hover:bg-[#FF4655]/90 text-white font-black uppercase tracking-[0.2em] transition-all transform hover:-translate-y-1 active:translate-y-0"
                                >
                                    Connect Wallet Now
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }

            {/* INTEL PROTOCOL */}
            <section className="px-10 pb-40 border-t border-white/5 pt-24 bg-gradient-to-b from-[#0F1923] to-black">
                <div className="max-w-7xl mx-auto">
                    <div className="flex flex-col md:flex-row gap-12 items-start">
                        <div className="md:w-1/3">
                            <h2 className="text-5xl font-black uppercase italic mb-6 leading-none tracking-tighter">Combat <br /><span className="text-[#FF4655]">Intel</span></h2>
                            <p className="text-[#8B978F] leading-relaxed">The StreamStack Oracle tracks every utility dump and weapon swap.</p>
                        </div>

                        <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                            <IntelCard icon={<Target size={24} />} title="Site Analysis" desc="Real-time probability of site takes based on team economy." />
                            <IntelCard icon={<Award size={24} />} title="MVP Tracking" desc="Earn status multipliers by backing the top performer." />
                            <IntelCard icon={<Trophy size={24} />} title="Clutch Bonus" desc="Massive XP rewards for identifying successful 1vX scenarios." />
                        </div>
                    </div>
                </div>
            </section>
        </div >
    );
};

const IntelCard = ({ icon, title, desc }) => (
    <div className="p-8 bg-white/5 border border-white/5 hover:border-[#FF4655]/20 transition-all group relative overflow-hidden">
        <div className="absolute top-0 right-0 w-16 h-16 bg-[#FF4655]/5 translate-x-8 -translate-y-8 rotate-45 group-hover:bg-[#FF4655]/10 transition-colors"></div>
        <div className="text-[#FF4655] mb-6">{icon}</div>
        <h3 className="text-xl font-black uppercase italic mb-3 tracking-tighter">{title}</h3>
        <p className="text-[#8B978F] text-sm leading-relaxed">{desc}</p>
    </div>
);

export default Home;