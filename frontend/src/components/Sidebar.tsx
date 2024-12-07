'use client';

import { useEffect, useState, useCallback } from 'react';
import { MessageSquarePlus, Loader2 } from 'lucide-react';
import { chatQueries } from '@/lib/queries';

interface Chat {
  id: number;
  messages: Array<{
    content: string;
    sender: string;
  }>;
}

interface SidebarProps {
  currentChatId: number;
  onChatSelect: (chatId: number) => void;
  onNewChat: () => void;
}

export default function Sidebar({ currentChatId, onChatSelect, onNewChat }: SidebarProps) {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchChats = useCallback(async () => {
    try {
      const data = await chatQueries.getAllChats();
      setChats(data);
    } catch (error) {
      console.error('Error fetching chats:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchChats();
  }, [fetchChats, currentChatId]);

  const getChatPreview = (chat: Chat) => {
    const firstMessage = chat.messages[0]?.content;
    return firstMessage ? 
      (firstMessage.length > 30 ? firstMessage.substring(0, 30) + '...' : firstMessage) 
      : 'New Chat';
  };

  return (
    <div className="w-64 bg-gray-900 h-screen flex flex-col p-2">
      <button
        onClick={onNewChat}
        className="flex items-center gap-2 p-4 text-white hover:bg-gray-800 w-full border border-gray-700 rounded-lg mb-2"
      >
        <MessageSquarePlus size={20} />
        New Chat
      </button>
      
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center p-4">
            <Loader2 className="w-6 h-6 text-white animate-spin" />
          </div>
        ) : (
          chats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => onChatSelect(chat.id)}
              className={`p-4 w-full text-left hover:bg-gray-800 
                ${chat.id === currentChatId ? 'bg-gray-800' : ''} 
                text-white truncate border-b border-gray-700`}
            >
              {getChatPreview(chat)}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
