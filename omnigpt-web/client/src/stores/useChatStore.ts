import create from 'zustand';
import { persist } from 'zustand/middleware';

interface ChatState {
  apiKey: string;
  history: ChatSession[];
  currentSession: ChatMessage[];
  selectedModel: string;
  actions: {
    setApiKey: (key: string) => void;
    newSession: () => void;
    addMessage: (message: ChatMessage) => void;
    switchModel: (modelId: string) => void;
  };
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      apiKey: '',
      history: [],
      currentSession: [],
      selectedModel: 'gpt-4',
      actions: {
        setApiKey: (key) => set({ apiKey: key }),
        newSession: () => set((state) => ({
          history: [...state.history, {
            id: Date.now(),
            messages: state.currentSession
          }],
          currentSession: []
        })),
        addMessage: (message) => set((state) => ({
          currentSession: [...state.currentSession, message]
        })),
        switchModel: (modelId) => set({ selectedModel: modelId })
      }
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({ 
        history: state.history,
        apiKey: '', // Never persist API key
        selectedModel: state.selectedModel
      })
    }
  )
);
