'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Upload } from 'lucide-react';
import { chatQueries } from '@/lib/queries';

interface Message {
  id: number;
  content: string;
  sender: 'user' | 'assistant';
}

interface ChatProps {
  chatId: number;
}

export default function Chat({ chatId }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const data = await chatQueries.getChat(chatId);
        setMessages(data.messages);
      } catch (error) {
        console.error('Error fetching messages:', error);
      }
    };

    fetchMessages();
  }, [chatId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setSelectedFile(file);
    setInput(`Selected file: ${file.name}`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && !selectedFile) || isLoading) return;

    setIsLoading(true);
    setIsTyping(true);

    try {
      if (selectedFile) {
        // Show file upload message immediately
        setMessages(prev => [...prev, {
          id: Date.now(),
          content: `Uploading file: "${selectedFile.name}"`,
          sender: 'user'
        }]);
        setInput(''); // Clear input immediately

        // Handle file upload
        await chatQueries.uploadFile(selectedFile, chatId);
        setMessages(prev => [...prev, {
          id: Date.now(),
          content: `File "${selectedFile.name}" uploaded and processed successfully`,
          sender: 'assistant'
        }]);
        setSelectedFile(null);
      } else {
        // Show user message immediately
        const userMessage = input;
        setMessages(prev => [...prev, { 
          id: Date.now(), 
          content: userMessage, 
          sender: 'user' 
        }]);
        setInput(''); // Clear input immediately

        // Then handle the response
        const data = await chatQueries.sendMessage(chatId, userMessage);
        setMessages(prev => [...prev, { 
          id: data.message_id, 
          content: data.response, 
          sender: 'assistant' 
        }]);
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        id: Date.now(),
        content: selectedFile 
          ? `Error uploading file "${selectedFile.name}". Please try again.`
          : "Sorry, there was an error processing your message.",
        sender: 'assistant'
      }]);
    } finally {
      setIsLoading(false);
      setIsTyping(false);
      setInput('');
      setSelectedFile(null);
    }
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setInput('');
  };

  return (
    <div className="flex flex-col h-screen bg-gray-800">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${
            message.sender === 'user' ? 'justify-end' : 'justify-start'
          }`}>
            <div className={`max-w-[80%] rounded-lg p-4 ${
              message.sender === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-white'
            }`}>
              {message.content}
            </div>
          </div>
        ))}
        
        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-700 text-white rounded-lg p-4 max-w-[80%]">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-white rounded-full animate-bounce" 
                     style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-white rounded-full animate-bounce" 
                     style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-white rounded-full animate-bounce" 
                     style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-gray-700 bg-gray-900 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-4 max-w-3xl mx-auto">
          <label className={`flex items-center justify-center w-10 h-10 rounded-full 
            bg-gray-800 hover:bg-gray-700 cursor-pointer ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}>
            <input
              type="file"
              className="hidden"
              onChange={handleFileSelect}
              accept=".txt,.pdf,.docx"
              disabled={isLoading}
            />
            <Upload className="w-5 h-5 text-gray-400" />
          </label>
          
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedFile ? 'File selected, click send to upload...' : 'Message ChatGPT...'}
            className="flex-1 bg-gray-800 text-white border-0 rounded-lg px-4 py-2 
              focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
            readOnly={selectedFile !== null}
          />
          
          {selectedFile && (
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white"
              disabled={isLoading}
            >
              Cancel
            </button>
          )}
          
          <button
            type="submit"
            disabled={isLoading || (!input.trim() && !selectedFile)}
            className="flex items-center justify-center w-10 h-10 rounded-full 
              bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 
              disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
