const API_URL = 'http://localhost:8000';

export const chatQueries = {
  createChat: async () => {
    const response = await fetch(`${API_URL}/chat/new`, {
      method: 'POST',
    });
    return response.json();
  },

  getChat: async (chatId: number) => {
    const response = await fetch(`${API_URL}/chat/${chatId}`);
    return response.json();
  },

  getAllChats: async () => {
    const response = await fetch(`${API_URL}/chats`);
    return response.json();
  },

  sendMessage: async (chatId: number, input: string) => {
    const response = await fetch(`${API_URL}/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chat_id: chatId,
        input,
      }),
    });
    return response.json();
  },

  uploadFile: async (file: File, chatId: number) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_URL}/ingest?chat_id=${chatId}`, {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },
};
