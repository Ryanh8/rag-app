'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Upload, Loader2 } from 'lucide-react';
import { chatQueries } from '@/lib/queries';

interface Message {
  id: number;
  content: string;
  sender: 'user' | 'assistant';
}

interface ChatProps {
  chatId: number;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isUploading: boolean;
  selectedFile: File | null;
  input: string;
  isTyping: boolean;
}

export default function Chat({ chatId }: ChatProps) {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: true,
    isUploading: false,
    selectedFile: null,
    input: '',
    isTyping: false
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setState(prev => ({ ...prev, isLoading: true }));
        const data = await chatQueries.getChat(chatId);
        setState(prev => ({ 
          ...prev, 
          messages: data.messages,
          isLoading: false 
        }));
      } catch (error) {
        console.error('Error fetching messages:', error);
        setState(prev => ({ ...prev, isLoading: false }));
      }
    };

    fetchMessages();
  }, [chatId]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setState(prev => ({
      ...prev,
      selectedFile: file,
      input: `Selected file: ${file.name}`
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const { input, selectedFile, isUploading, isLoading } = state;
    
    if ((!input.trim() && !selectedFile) || isUploading || isLoading) return;

    try {
      if (selectedFile) {
        setState(prev => ({ 
          ...prev, 
          isUploading: true,
          messages: [...prev.messages, {
            id: Date.now(),
            content: `Uploading file: "${selectedFile.name}"`,
            sender: 'user'
          }]
        }));

        await chatQueries.uploadFile(selectedFile, chatId);
        
        setState(prev => ({
          ...prev,
          messages: [...prev.messages, {
            id: Date.now(),
            content: `File "${selectedFile.name}" uploaded and processed successfully`,
            sender: 'assistant'
          }],
          selectedFile: null,
          input: '',
          isUploading: false
        }));
      } else {
        const userMessage = input;
        setState(prev => ({
          ...prev,
          isTyping: true,
          messages: [...prev.messages, { 
            id: Date.now(), 
            content: userMessage, 
            sender: 'user' 
          }],
          input: ''
        }));

        const data = await chatQueries.sendMessage(chatId, userMessage);
        
        setState(prev => ({
          ...prev,
          messages: [...prev.messages, { 
            id: data.message_id, 
            content: data.response, 
            sender: 'assistant' 
          }],
          isTyping: false
        }));
      }
    } catch (error) {
      console.error('Error:', error);
      setState(prev => ({
        ...prev,
        messages: [...prev.messages, {
          id: Date.now(),
          content: selectedFile 
            ? `Error uploading file "${selectedFile.name}". Please try again.`
            : "Sorry, there was an error processing your message.",
          sender: 'assistant'
        }],
        isTyping: false,
        isUploading: false
      }));
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-800">
      {state.isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-white animate-spin" />
        </div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {state.messages.map((message) => (
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
            
            {(state.isTyping || state.isUploading) && (
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
                bg-gray-800 hover:bg-gray-700 cursor-pointer 
                ${(state.isUploading || state.isLoading) ? 'opacity-50 cursor-not-allowed' : ''}`}>
                <input
                  type="file"
                  className="hidden"
                  onChange={handleFileSelect}
                  accept=".txt,.pdf,.docx"
                  disabled={state.isUploading || state.isLoading}
                />
                <Upload className="w-5 h-5 text-gray-400" />
              </label>
              
              <input
                type="text"
                value={state.input}
                onChange={(e) => setState(prev => ({ ...prev, input: e.target.value }))}
                placeholder={state.selectedFile ? 'File selected, click send to upload...' : 'Message ChatGPT...'}
                className="flex-1 bg-gray-800 text-white border-0 rounded-lg px-4 py-2 
                  focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={state.isUploading || state.isLoading}
                readOnly={state.selectedFile !== null}
              />
              
              {state.selectedFile && (
                <button
                  type="button"
                  onClick={() => setState(prev => ({ 
                    ...prev, 
                    selectedFile: null, 
                    input: '' 
                  }))}
                  className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white"
                  disabled={state.isUploading || state.isLoading}
                >
                  Cancel
                </button>
              )}

              <button
                type="submit"
                disabled={state.isUploading || state.isLoading || (!state.input.trim() && !state.selectedFile)}
                className="flex items-center justify-center w-10 h-10 rounded-full 
                  bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 
                  disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </>
      )}
    </div>
  );
}
