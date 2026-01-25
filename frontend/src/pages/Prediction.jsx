import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Users, ArrowLeft, Copy, Check } from 'lucide-react';
import { useWallet } from '../context/WalletContext';

const Prediction = () => {
    const navigate = useNavigate();
    const { walletConnected } = useWallet();

    const [alias, setAlias] = useState('');
    const [roomCode, setRoomCode] = useState('');
    const [ytUrl, setYtUrl] = useState('');

    useEffect(() => {
        if (!walletConnected) {
            navigate('/');
        }
    }, [walletConnected, navigate]);

    const isValidYoutubeUrl = (url) => {
        if (!url || !url.trim()) return false;

        const patterns = [
            /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/live\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[\w-]+/
        ];

        return patterns.some(pattern => pattern.test(url.trim()));
    };

    const handleCreateRoom = () => {
        // Validate inputs
        if (!alias.trim()) {
            alert("Please enter an alias");
            return;
        }

        if (!ytUrl.trim()) {
            alert("Please enter a YouTube URL");
            return;
        }

        if (!isValidYoutubeUrl(ytUrl)) {
            alert("Invalid YouTube URL! Please enter a valid YouTube link.\n\nSupported formats:\n- youtube.com/watch?v=...\n- youtu.be/...\n- youtube.com/live/...\n- youtube.com/shorts/...");
            return;
        }

        // Generate room ID
        const newRoomId = Math.random().toString(36).substring(2, 9).toUpperCase();

        // In a real app, you would store the room data (roomId, ytUrl) to Firebase/backend here
        // For now, we'll pass the URL via query params
        const encodedUrl = encodeURIComponent(ytUrl.trim());
        navigate(`/room/${newRoomId}?url=${encodedUrl}&alias=${encodeURIComponent(alias.trim())}`);
    };

    const handleJoinRoom = () => {
        if (!alias.trim()) {
            alert("Please enter an alias");
            return;
        }

        if (!roomCode.trim()) {
            alert("Please enter a room code");
            return;
        }

        // Navigate to room - the Room component will fetch the URL from backend/Firebase
        // For now, joining without URL will show "No Stream Source" message
        navigate(`/room/${roomCode.trim().toUpperCase()}?alias=${encodeURIComponent(alias.trim())}`);
    };

    return (
        <div className="min-h-screen font-sans bg-[#0F1923] text-[#ECE8E1] flex items-center justify-center p-10">
            <div className="max-w-2xl w-full bg-[#0F1923] border border-white/10 p-10 shadow-[20px_20px_0px_0px_rgba(255,70,85,0.1)] relative">
                <button
                    onClick={() => navigate('/')}
                    className="absolute -top-12 left-0 flex items-center gap-2 text-[#8B978F] hover:text-[#FF4655] transition-colors group"
                >
                    <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                    <span className="text-[10px] font-black uppercase tracking-[0.2em]">Return to Home</span>
                </button>

                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#FF4655] to-transparent"></div>

                <h2 className="text-4xl font-black uppercase italic mb-8 tracking-tighter">
                    Operator <span className="text-[#FF4655]">Setup</span>
                </h2>

                <div className="space-y-8">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black uppercase tracking-[0.2em] text-[#8B978F]">Identify Yourself</label>
                        <input
                            type="text"
                            value={alias}
                            onChange={(e) => setAlias(e.target.value)}
                            placeholder="ENTER ALIAS"
                            maxLength={20}
                            className="w-full bg-white/5 border border-white/10 px-6 py-4 text-xl font-bold uppercase tracking-widest focus:border-[#FF4655] outline-none text-white placeholder-white/20 transition-all"
                        />
                    </div>

                    <div className="grid md:grid-cols-2 gap-8">
                        {/* CREATE ROOM */}
                        <div className="space-y-4 p-6 bg-white/5 border border-white/5 hover:border-[#FF4655]/30 transition-all">
                            <h3 className="text-xl font-black uppercase italic tracking-tight flex items-center gap-3">
                                <Zap size={20} className="text-[#FF4655]" /> Create Room
                            </h3>
                            <div className="space-y-3">
                                <input
                                    type="text"
                                    value={ytUrl}
                                    onChange={(e) => setYtUrl(e.target.value)}
                                    placeholder="YOUTUBE LIVE URL"
                                    className="w-full bg-black/20 border border-white/10 px-4 py-3 text-sm font-mono focus:border-[#FF4655] outline-none text-white placeholder-white/30"
                                />
                                <div className="text-[9px] text-[#8B978F] font-mono leading-relaxed">
                                    The video will be shared with all room members
                                </div>
                                <button
                                    onClick={handleCreateRoom}
                                    className="w-full py-3 bg-[#FF4655] text-white font-black uppercase tracking-[0.2em] text-sm hover:bg-[#FF4655]/90 transition-colors"
                                >
                                    Initialize
                                </button>
                            </div>
                        </div>

                        {/* JOIN ROOM */}
                        <div className="space-y-4 p-6 bg-white/5 border border-white/5 hover:border-[#22D3EE]/30 transition-all">
                            <h3 className="text-xl font-black uppercase italic tracking-tight flex items-center gap-3">
                                <Users size={20} className="text-[#22D3EE]" /> Join Room
                            </h3>
                            <div className="space-y-3">
                                <input
                                    type="text"
                                    value={roomCode}
                                    onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
                                    placeholder="ROOM CODE"
                                    maxLength={10}
                                    className="w-full bg-black/20 border border-white/10 px-4 py-3 text-sm font-mono focus:border-[#22D3EE] outline-none text-white placeholder-white/30 uppercase"
                                />
                                <div className="text-[9px] text-[#8B978F] font-mono leading-relaxed">
                                    Enter code to join existing room
                                </div>
                                <button
                                    onClick={handleJoinRoom}
                                    className="w-full py-3 bg-[#22D3EE] text-[#0F1923] font-black uppercase tracking-[0.2em] text-sm hover:bg-[#22D3EE]/90 transition-colors"
                                >
                                    Connect
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* INFO NOTE */}
                    <div className="mt-8 p-4 bg-white/5 border-l-2 border-[#FF4655]">
                        <p className="text-[10px] font-mono text-[#8B978F] leading-relaxed">
                            <span className="text-[#FF4655] font-black">NOTE:</span> When you create a room, share the room code with others.
                            They can join using just the code - the video will be automatically loaded for all participants.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Prediction;