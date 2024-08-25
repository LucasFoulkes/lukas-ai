import { useState, useEffect, useRef } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';

// Custom hook for managing WebSocket connection and input state
const useBooks = () => {
    const [input, setInput] = useState(''); // User input state
    const [wsMessages, setWsMessages] = useState([]); // WebSocket messages state
    const ws = useRef(null); // WebSocket instance
    const navigate = useNavigate();

    useEffect(() => {
        // Initialize WebSocket connection
        ws.current = new WebSocket('ws://localhost:8000/ws');

        ws.current.onopen = () => console.log('WebSocket connection opened');

        ws.current.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
            setWsMessages((prevMessages) => [...prevMessages, event.data]);
        };

        ws.current.onerror = (error) => console.error('WebSocket error:', error);

        ws.current.onclose = () => console.log('WebSocket connection closed');

        // Cleanup WebSocket connection on component unmount
        return () => {
            if (ws.current) {
                ws.current.close();
            }
        };
    }, []);

    const handleCommand = (event) => {
        event.preventDefault();
        const command = input.trim();

        if (command && ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(command);
        }

        if (['back', 'exit'].includes(command.toLowerCase())) {
            navigate({ to: '/' });
        }

        setInput(''); // Clear input field after command execution
    };

    return { wsMessages, input, setInput, handleCommand };
};

// Component for handling book commands
function Books() {
    const { wsMessages, input, setInput, handleCommand } = useBooks();

    return (
        <form onSubmit={handleCommand} className="flex flex-col items-center justify-center h-screen font-fira">
            {/* Command input */}
            <div className="flex items-center space-x-2 max-w-md w-full p-4 border-t border-b border-gray-300">
                <span>(books)lukybooks@root:~$</span>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="flex-grow bg-transparent border-none outline-none"
                    autoFocus
                />
            </div>

            {/* WebSocket messages display */}
            <div className="mt-4 max-h-[300px] ">
                {wsMessages.map((msg, index) => (
                    <p key={index} className="text-blue-700 text-justify truncate">
                        {msg}
                    </p>
                ))}
            </div>
        </form>
    );
}

// Route configuration
export const Route = createFileRoute('/f2x9b0o7k')({ component: Books });

export default Books;
