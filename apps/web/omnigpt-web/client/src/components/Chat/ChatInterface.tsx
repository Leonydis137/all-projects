import { useChatStore } from '../../stores/useChatStore';

const ChatInterface = () => {
  const { currentSession, actions } = useChatStore();
  const [input, setInput] = useState('');

  const handleSubmit = async () => {
    actions.addMessage({ role: 'user', content: input });
    
    try {
      const response = await apiClient.post('/chat', {
        message: input,
        model: useChatStore.getState().selectedModel
      });
      
      actions.addMessage(response.data);
    } catch (error) {
      showErrorToast('Failed to send message');
    }
    
    setInput('');
  };

  return (
    <div className="chat-container">
      <MessageList messages={currentSession} />
      <InputPanel 
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
      />
    </div>
  );
};
