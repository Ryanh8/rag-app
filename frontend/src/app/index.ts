export interface Message {
  id: number;
  content: string;
  sender: 'user' | 'assistant';
}

export interface Chat {
  id: number;
  messages: Message[];
}
