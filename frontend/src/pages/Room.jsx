import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Users, MessageSquare, Activity, Plus, Minus, AlertTriangle, X, ChevronRight, Wallet, Download } from 'lucide-react';
import { useWallet } from '../context/WalletContext';
import { useBetting } from '../hooks/useBetting';
import { rtdb } from '../firebase';
import { ref, onValue, off, push, set, query, limitToLast } from "firebase/database";

const Room = () => {
    // 1. GET WALLET ID (Needed for betting identity)
    const { walletConnected, walletId } = useWallet();

    const { depositFunds, withdrawFunds, loading: isTransacting } = useBetting();
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const ytUrl = decodeURIComponent(searchParams.get('url') || '');
    const alias = searchParams.get('alias') || 'Guest';
    const playerRef = useRef(null);
    const [playerReady, setPlayerReady] = useState(false);

    // --- VIDEO URL PARSING ---
    const getVideoId = (url) => {
        if (!url) return '';
        try {
            const cleanUrl = url.trim();
            const validUrl = cleanUrl.startsWith('http') ? cleanUrl : `https://${cleanUrl}`;
            const parsed = new URL(validUrl);
            let videoId = '';

            if (parsed.hostname.includes('youtube.com') && parsed.searchParams.get('v')) {
                videoId = parsed.searchParams.get('v');
            }
            else if (parsed.pathname.startsWith('/shorts/')) {
                videoId = parsed.pathname.split('/shorts/')[1].split('?')[0];
            }
            else if (parsed.hostname.includes('youtu.be')) {
                videoId = parsed.pathname.substring(1).split('?')[0];
            }
            else if (parsed.pathname.startsWith('/embed/')) {
                videoId = parsed.pathname.split('/embed/')[1].split('?')[0];
            }
            else if (parsed.pathname.startsWith('/live/')) {
                videoId = parsed.pathname.split('/live/')[1].split('?')[0];
            }

            if (!videoId) return '';
            videoId = videoId.split('&')[0].split('#')[0];
            return videoId;
        } catch (e) {
            console.error("Invalid YouTube URL:", e);
            return '';
        }
    };

    const videoId = getVideoId(ytUrl);

    // --- STATE ---
    const [phase, setPhase] = useState('BETTING');
    const [scoreBlue, setScoreBlue] = useState(0);
    const [scoreRed, setScoreRed] = useState(0);
    const [userPoints, setUserPoints] = useState(0); // Default to 0, load real balance below
    const [betAmount, setBetAmount] = useState(10);
    const [chatMessage, setChatMessage] = useState('');
    const [messages, setMessages] = useState([
        { user: 'System', text: `Welcome to Room ${id}. Betting is OPEN.` },
    ]);
    const [showFundsModal, setShowFundsModal] = useState(false);

    // --- FIREBASE LOGIC ---
    useEffect(() => {
        const activeRoundRef = ref(rtdb, `lobbies/${id}/active_round`);

        const handleActiveRound = (snapshot) => {
            const currentRoundId = snapshot.val();
            if (currentRoundId) {
                const roundPath = `lobbies/${id}/rounds/${currentRoundId}`;
                const roundRef = ref(rtdb, roundPath);

                const handleRoundUpdate = (roundSnapshot) => {
                    const data = roundSnapshot.val();
                    if (data) {
                        if (data.phase) setPhase(data.phase);
                        if (data.scores) {
                            if (data.scores.own !== undefined) setScoreBlue(data.scores.own);
                            if (data.scores.enemy !== undefined) setScoreRed(data.scores.enemy);
                        } else {
                            if (data.own_score !== undefined) setScoreBlue(data.own_score);
                            if (data.enemy_score !== undefined) setScoreRed(data.enemy_score);
                        }
                    }
                };

                onValue(roundRef, handleRoundUpdate);
                return () => off(roundRef);
            }
        };

        onValue(activeRoundRef, handleActiveRound);

        const chatRef = query(ref(rtdb, `lobbies/${id}/chat`), limitToLast(50));
        const handleChat = (snapshot) => {
            const data = snapshot.val();
            if (data) {
                const messageList = Object.values(data)
                    .sort((a, b) => (a.timestamp || 0) - (b.timestamp || 0))
                    .map(msg => ({ user: msg.user, text: msg.text }));
                setMessages(messageList);
            } else {
                setMessages([{ user: 'System', text: `Welcome to Room ${id}. Waiting for comms...` }]);
            }
        };

        onValue(chatRef, handleChat);

        // --- NEW: LISTEN TO USER BALANCE ---
        if (walletId) {
            const balanceRef = ref(rtdb, `users/${walletId.toLowerCase()}/balance`);
            const handleBalance = (snapshot) => {
                const bal = snapshot.val();
                if (bal !== null) setUserPoints(bal);
            };
            onValue(balanceRef, handleBalance);
            return () => {
                off(activeRoundRef);
                off(chatRef);
                off(balanceRef);
            };
        }

        return () => {
            off(activeRoundRef);
            off(chatRef);
        };
    }, [id, walletId]);

    // --- WALLET CHECK ---
    useEffect(() => {
        if (!walletConnected) {
            navigate('/');
        }
    }, [walletConnected, navigate]);

    // --- YOUTUBE PLAYER ---
    useEffect(() => {
        if (!videoId) return;
        if (window.YT && window.YT.Player) {
            initPlayer();
            return;
        }
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        window.onYouTubeIframeAPIReady = initPlayer;
        return () => { window.onYouTubeIframeAPIReady = null; };
    }, [videoId]);

    const initPlayer = () => {
        if (!videoId || !window.YT) return;
        try {
            playerRef.current = new window.YT.Player('youtube-player', {
                videoId: videoId,
                playerVars: { autoplay: 0, controls: 1, modestbranding: 1, rel: 0, fs: 1, playsinline: 1 },
                events: {
                    onReady: () => setPlayerReady(true),
                    onError: (event) => console.error('YouTube player error:', event.data)
                }
            });
        } catch (error) { console.error('Failed to initialize YouTube player:', error); }
    };

    // --- DEPOSIT HANDLER ---
    const handleDeposit = async () => {
        const amountStr = prompt("Enter amount of StreamCoin (STRM) to deposit:");
        if (!amountStr) return;

        const amount = parseFloat(amountStr);
        if (isNaN(amount) || amount <= 0) {
            alert("Please enter a valid amount.");
            return;
        }

        const success = await depositFunds(amountStr);
        // Note: We removed the optimistic update here because the Firebase listener (added above) will handle it
    };

    // --- WITHDRAW HANDLER ---
    const handleWithdraw = async () => {
        const amountStr = prompt(`Balance: ${userPoints} pts.\nHow much to withdraw?`);
        if (!amountStr) return;

        const amount = parseFloat(amountStr);
        if (isNaN(amount) || amount <= 0 || amount > userPoints) {
            alert("Invalid amount or insufficient funds.");
            return;
        }

        const success = await withdrawFunds(amount);
    };

    // --- BETTING HANDLER (FIXED) ---
    const handleBet = (outcome) => {
        if (phase !== 'BETTING') return;

        if (!walletId) {
            alert("Wallet not connected!");
            return;
        }

        if (userPoints >= betAmount) {
            // Optimistic update
            setUserPoints(prev => prev - betAmount);

            const betRef = push(ref(rtdb, `bets/${id}`));
            set(betRef, {
                user: walletId, // <--- CRITICAL FIX: SEND WALLET ADDRESS
                alias: alias,   // Optional: Store alias for display logic later
                amount: betAmount,
                outcome: outcome,
                timestamp: Date.now()
            });
            setMessages(prev => [...prev, { user: 'System', text: `You bet ${betAmount} on ${outcome}` }]);
        } else {
            setShowFundsModal(true);
        }
    };

    // --- CHAT HANDLER ---
    const handleSendMessage = async () => {
        if (!chatMessage.trim()) return;
        try {
            const newMsgRef = push(ref(rtdb, `lobbies/${id}/chat`));
            await set(newMsgRef, {
                user: alias, // Chat can still use Alias
                text: chatMessage,
                timestamp: Date.now()
            });
            setChatMessage('');
        } catch (e) { console.error("Failed to send message", e); }
    };

    const messagesEndRef = React.useRef(null);
    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    useEffect(() => scrollToBottom(), [messages]);

    return (
        <div className="h-[calc(100vh-97px)] overflow-hidden bg-[#0F1923] text-[#ECE8E1] flex flex-col">
            <div className="flex-1 flex overflow-hidden">
                {/* MAIN STREAM AREA */}
                <div className="flex-1 relative bg-black flex flex-col justify-center select-none">
                    {videoId ? (
                        <div className='relative w-full h-full'>
                            <div id="youtube-player" className="w-full h-full"></div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center gap-4">
                            <AlertTriangle size={48} className="text-[#FF4655]" />
                            <p className="text-[#8B978F] text-lg">No Stream Source Provided</p>
                        </div>
                    )}

                    {/* LIVE HUD OVERLAY */}
                    <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-8 bg-[#0F1923]/90 px-8 py-4 border-b-2 border-[#FF4655] shadow-lg backdrop-blur-sm pointer-events-none select-none z-[50]">
                        <span className="text-4xl font-black italic text-[#22D3EE]">{scoreBlue}</span>
                        <div className="flex flex-col items-center">
                            <span className="text-[10px] font-bold uppercase text-[#8B978F] tracking-[0.2em] mb-1">Round 12</span>
                            <div className="flex items-center gap-2">
                                {phase === 'BETTING' && <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>}
                                <span className={`font-black uppercase tracking-widest ${phase === 'BETTING' ? 'text-green-500' : 'text-[#FF4655]'}`}>
                                    {phase}
                                </span>
                            </div>
                        </div>
                        <span className="text-4xl font-black italic text-[#FF4655]">{scoreRed}</span>
                    </div>
                </div>

                {/* SIDEBAR INTERACTION */}
                <div className="w-[400px] border-l border-white/10 bg-[#0F1923] flex flex-col">

                    {/* SIDEBAR HEADER */}
                    <div className="p-6 border-b border-white/10 bg-[#0F1923]">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-4">
                                <button onClick={() => navigate('/')} className="hover:text-[#FF4655] transition-colors">
                                    <ArrowLeft />
                                </button>
                                <span className="font-black uppercase tracking-wider text-lg">
                                    Room: <span className="text-[#FF4655]">{id}</span>
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <Users size={16} className="text-[#8B978F]" />
                                <span className="font-mono text-sm">124</span>
                            </div>
                        </div>

                        {/* UPDATED BALANCE & WALLET BOX */}
                        <div className="bg-white/5 rounded-sm border border-white/5 p-3">
                            <div className="flex items-center justify-between mb-3">
                                <span className="text-[10px] font-black uppercase text-[#8B978F] tracking-widest">Balance</span>
                                <span className="font-mono font-bold text-[#FF4655]">{userPoints} pts</span>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                {/* Deposit Button */}
                                <button
                                    onClick={handleDeposit}
                                    disabled={isTransacting}
                                    className={`py-2 border text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2
                                        ${isTransacting
                                            ? 'bg-white/5 border-white/10 text-white/20 cursor-wait'
                                            : 'bg-[#22D3EE]/10 border-[#22D3EE]/50 text-[#22D3EE] hover:bg-[#22D3EE] hover:text-[#0F1923]'
                                        }`}
                                >
                                    <Wallet size={12} /> Deposit
                                </button>

                                {/* Withdraw Button */}
                                <button
                                    onClick={handleWithdraw}
                                    disabled={isTransacting}
                                    className={`py-2 border text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2
                                        ${isTransacting
                                            ? 'bg-white/5 border-white/10 text-white/20 cursor-wait'
                                            : 'bg-[#FF4655]/10 border-[#FF4655]/50 text-[#FF4655] hover:bg-[#FF4655] hover:text-white'
                                        }`}
                                >
                                    <Download size={12} /> Withdraw
                                </button>
                            </div>

                            {isTransacting && (
                                <div className="mt-2 text-[9px] text-center text-[#8B978F] animate-pulse font-mono uppercase tracking-wider">
                                    // Processing Blockchain Tx...
                                </div>
                            )}
                        </div>
                    </div>

                    {/* BETTING CONTROLS */}
                    <div className="p-6 border-b border-white/10 bg-black/20">
                        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-[#8B978F] mb-4 flex items-center gap-2">
                            <Activity size={14} /> Live Markets
                        </h3>

                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <button
                                disabled={phase !== 'BETTING'}
                                onClick={() => handleBet('WIN')}
                                className={`py-6 border-2 border-[#22D3EE]/20 bg-[#22D3EE]/5 hover:bg-[#22D3EE]/10 transition-all uppercase font-black italic text-xl tracking-tighter
                                    ${phase !== 'BETTING' ? 'opacity-50 cursor-not-allowed grayscale' : 'hover:border-[#22D3EE]'} text-[#22D3EE]`}
                            >
                                Bet Win
                            </button>
                            <button
                                disabled={phase !== 'BETTING'}
                                onClick={() => handleBet('LOSS')}
                                className={`py-6 border-2 border-[#FF4655]/20 bg-[#FF4655]/5 hover:bg-[#FF4655]/10 transition-all uppercase font-black italic text-xl tracking-tighter
                                    ${phase !== 'BETTING' ? 'opacity-50 cursor-not-allowed grayscale' : 'hover:border-[#FF4655]'} text-[#FF4655]`}
                            >
                                Bet Loss
                            </button>
                        </div>

                        {/* BET ADJUSTMENT */}
                        <div className="flex items-center justify-between bg-black/40 p-3 mb-4 border border-white/5">
                            <span className="text-[10px] font-black uppercase text-[#8B978F] tracking-widest">Wager</span>
                            <div className="flex items-center gap-4">
                                <button
                                    onClick={() => setBetAmount(prev => Math.max(10, prev - 10))}
                                    className="p-1 hover:text-[#FF4655] transition-colors"
                                >
                                    <Minus size={14} />
                                </button>
                                <span className="font-mono font-bold text-xl w-12 text-center text-white">{betAmount}</span>
                                <button
                                    onClick={() => setBetAmount(prev => Math.min(1000, prev + 10))}
                                    className="p-1 hover:text-[#22D3EE] transition-colors"
                                >
                                    <Plus size={14} />
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center justify-between text-[10px] font-mono text-[#8B978F] uppercase">
                            <span>Min: 10 pts</span>
                            <span>Max: 1000 pts</span>
                        </div>
                    </div>

                    {/* CHAT */}
                    <div className="flex-1 flex flex-col min-h-0">
                        <div className="p-4 border-b border-white/5 bg-[#0F1923]">
                            <span className="text-xs font-black uppercase tracking-[0.2em] text-[#8B978F] flex items-center gap-2">
                                <MessageSquare size={14} /> Live Comms
                            </span>
                        </div>
                        <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-sm">
                            {messages.map((msg, idx) => (
                                <div key={idx} className={`${msg.user === 'System' ? 'text-[#FF4655] italic' : 'text-[#ECE8E1]'}`}>
                                    <span className="opacity-50 font-bold mr-2 uppercase text-[10px] tracking-wider">{msg.user}:</span>
                                    <span>{msg.text}</span>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                        <div className="p-4 border-t border-white/10 bg-black/20">
                            <div className="relative">
                                <input
                                    type="text"
                                    value={chatMessage}
                                    onChange={(e) => setChatMessage(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                                    placeholder="TRANSMIT MESSAGE..."
                                    className="w-full bg-[#0F1923] border border-white/10 pl-4 pr-10 py-3 text-xs font-bold uppercase tracking-wider focus:border-[#FF4655] outline-none text-white placeholder-white/20"
                                />
                                <button
                                    onClick={handleSendMessage}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-[#FF4655] hover:text-white transition-colors"
                                >
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* INSUFFICIENT FUNDS MODAL */}
            {showFundsModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setShowFundsModal(false)}></div>
                    <div className="relative w-full max-w-sm bg-[#0F1923] border border-[#FF4655] p-6 shadow-[0_0_50px_rgba(255,70,85,0.2)] animate-[fadeIn_0.2s_ease-out]">
                        <button onClick={() => setShowFundsModal(false)} className="absolute top-4 right-4 text-[#8B978F] hover:text-white transition-colors">
                            <X size={20} />
                        </button>
                        <div className="flex flex-col items-center text-center">
                            <div className="w-12 h-12 rounded-full bg-[#FF4655]/10 flex items-center justify-center mb-4 border border-[#FF4655]/20">
                                <AlertTriangle size={24} className="text-[#FF4655]" />
                            </div>
                            <h3 className="text-xl font-black italic uppercase tracking-tighter mb-2">Insufficient Funds</h3>
                            <p className="text-[#8B978F] mb-6 leading-relaxed font-medium text-sm">
                                You require more points to place this wager. Please deposit more crypto.
                            </p>
                            <button
                                onClick={() => {
                                    setShowFundsModal(false);
                                    handleDeposit();
                                }}
                                className="w-full py-3 bg-[#FF4655] hover:bg-[#FF4655]/90 text-white font-black uppercase tracking-[0.2em] transition-all"
                            >
                                Deposit Now
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
                .scrollbar-hide::-webkit-scrollbar { display: none; }
                ::-webkit-scrollbar { width: 6px; }
                ::-webkit-scrollbar-track { background: #0F1923; }
                ::-webkit-scrollbar-thumb { background: #FF4655; border-radius: 3px; }
                ::-webkit-scrollbar-thumb:hover { background: #D93444; }
                .cursor-wait { cursor: wait; }
            `}</style>
        </div>
    );
};

export default Room;