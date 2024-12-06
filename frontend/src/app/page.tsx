'use client';

import { useEffect, useState } from 'react';
import Chat from '@/components/Chat';
import Sidebar from '@/components/Sidebar';
import { Loader2 } from 'lucide-react';
import { chatQueries } from '@/lib/queries';

export default function Home() {
  const [chatId, setChatId] = useState<number | null>(null);

  const createNewChat = async () => {
    try {
      const data = await chatQueries.createChat();
      setChatId(data.chat_id);
    } catch (error) {
      console.error('Error creating chat:', error);
    }
  };

  useEffect(() => {
    const initializeChat = async () => {
      if (!chatId) {
        await createNewChat();
      }
    };
    initializeChat();
  }, [chatId]);

  if (!chatId) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-900">
        <Loader2 className="w-8 h-8 text-white animate-spin" />
      </div>
    );
  }

  return (
    <main className="flex h-screen bg-gray-900">
      <Sidebar
        currentChatId={chatId}
        onChatSelect={setChatId}
        onNewChat={createNewChat}
      />
      <div className="flex-1">
        <Chat chatId={chatId} />
      </div>
    </main>
  );
}
