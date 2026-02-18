import React, { useState, useEffect } from 'react';
import { Heart, MessageCircle, Share2, User } from 'lucide-react';

// === CONFIGURATION ===
const API_BASE = "http://localhost:5000";

const SocialFeed = () => {
  const [posts, setPosts] = useState([]);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  // === AUTH ===
  const login = async (username, password) => {
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (data.token) {
        setToken(data.token);
        localStorage.setItem('token', data.token);
        loadFeed();
      }
    } catch (err) {
      console.error("Login failed", err);
    }
  };

  // === FEED ===
  const loadFeed = async () => {
    setLoading(true);
    // In a real app, strict-mode double-fetch protection would be needed
    // Mocking feed data for demo purposes since backend isn't running
    setTimeout(() => {
        setPosts([
            { id: 1, author: "Overlord", content: "System initialization complete.", likes: 128 },
            { id: 2, author: "Nexus", content: "Deploying new social architecture...", likes: 64 },
            { id: 3, author: "User_42", content: "The feed algorithm is surprisingly snappy!", likes: 12 }
        ]);
        setLoading(false);
    }, 800);
  };

  useEffect(() => {
    if (token) loadFeed();
  }, [token]);

  // === RENDER ===
  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-900 text-white">
        <h1 className="text-3xl font-bold mb-8">Nexus Social</h1>
        <div className="bg-gray-800 p-8 rounded-lg shadow-xl w-96">
            <input type="text" placeholder="Username" className="w-full mb-4 p-2 bg-gray-700 rounded" />
            <input type="password" placeholder="Password" className="w-full mb-6 p-2 bg-gray-700 rounded" />
            <button 
                onClick={() => login("admin", "overlord")}
                className="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded font-bold"
            >
                Login to Nexus
            </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6 border-b border-gray-700 pb-4">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                Nexus Stream
            </h1>
            <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">Connected</span>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            </div>
        </div>

        {/* Feed Stream */}
        {loading ? (
            <div className="text-center py-12 text-gray-500">Syncing timelines...</div>
        ) : (
            <div className="space-y-4">
                {posts.map(post => (
                    <div key={post.id} className="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-gray-600 transition-colors">
                        <div className="flex items-start gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                                <User size={20} />
                            </div>
                            <div className="flex-1">
                                <div className="flex justify-between">
                                    <h3 className="font-bold text-gray-200">{post.author}</h3>
                                    <span className="text-xs text-gray-500">2m ago</span>
                                </div>
                                <p className="text-gray-300 mt-1 mb-3">{post.content}</p>
                                
                                {/* Actions */}
                                <div className="flex gap-6 text-gray-400 text-sm">
                                    <button className="flex items-center gap-1 hover:text-red-400">
                                        <Heart size={16} /> {post.likes}
                                    </button>
                                    <button className="flex items-center gap-1 hover:text-blue-400">
                                        <MessageCircle size={16} /> Reply
                                    </button>
                                    <button className="flex items-center gap-1 hover:text-green-400">
                                        <Share2 size={16} /> Share
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        )}
      </div>
    </div>
  );
};

export default SocialFeed;
