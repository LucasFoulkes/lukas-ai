import { useState, useEffect } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import ky from 'ky';

interface ApiResponse {
    message: string;
    data: any[]; // Consider using a more specific type if possible
}

const useBooks = () => {
    const [response, setResponse] = useState<ApiResponse>({ message: '', data: [] });
    const [wsMessages, setWsMessages] = useState<string[]>([]);
    const [input, setInput] = useState('');
    const navigate = useNavigate();

    const fetchData = async (command = 'init') => {
        try {
            const result = await ky.get(`http://localhost:8000/book/${command}`).json<ApiResponse>();
            setResponse(result);
        } catch (error) {
            setResponse({ message: 'Failed to fetch data', data: [] });
            console.error('Error fetching data:', error);
        }
    };

    useEffect(() => {
        fetchData();

        // Set up WebSocket connection
        const ws = new WebSocket('ws://localhost:8000/ws');

        ws.onopen = () => {
            console.log('WebSocket connection opened');
        };

        ws.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
            setWsMessages((prevMessages) => [...prevMessages, event.data]);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('WebSocket connection closed');
        };

        // Cleanup function to disconnect when component unmounts
        return () => {
            ws.close();
            ky.get('http://localhost:8000/book/disconnect')
                .then(() => console.log('Disconnected from IRC server'))
                .catch(error => console.error('Error disconnecting:', error));
        };
    }, []);

    const handleCommand: React.FormEventHandler<HTMLFormElement> = (event) => {
        event.preventDefault();
        const command = input;
        if (['back', 'exit'].includes(command.toLowerCase())) {
            navigate({ to: '/' });
        } else {
            fetchData(encodeURIComponent(command));
        }
        setInput('');
    };

    return { response, wsMessages, input, setInput, handleCommand };
};

export const Route = createFileRoute('/f2x9b0o7k')({ component: Books });

function Books() {
    const { response, wsMessages, input, setInput, handleCommand } = useBooks();

    return (
        <>
            <form onSubmit={handleCommand} className="flex flex-col items-center justify-center h-screen font-fira">
                <div className="flex items-center space-x-2 max-w-md w-full p-4 border-t border-b border-gray-300">
                    <span>(books)lukybooks@root:~$</span>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        style={{ flexGrow: 1, background: 'transparent', border: 'none', outline: 'none' }}
                        autoFocus
                    />
                </div>
                {response.message && (
                    <p style={{ marginTop: '0.5rem', color: response.message.startsWith('Failed') ? 'red' : 'gray', textAlign: 'justify' }}>
                        {response.message}
                    </p>
                )}
                <div style={{ marginTop: '1rem', maxHeight: '300px', overflowY: 'scroll' }}>
                    <h3>WebSocket Messages:</h3>
                    {wsMessages.map((msg, index) => (
                        <p key={index} style={{ textAlign: 'justify', color: 'blue' }}>
                            {msg}
                        </p>
                    ))}
                </div>
            </form>
        </>
    );
}

export default Books;
