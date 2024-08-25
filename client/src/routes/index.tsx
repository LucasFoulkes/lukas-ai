import { useState, useEffect, useRef } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';

// Passphrase to URL mappings
const PASSPHRASE_MAPPINGS: { [key: string]: string } = {
    coyoteblue: '/f2x9b0o7k',
    cananvalley: 'https://cananvalley.systems/',
};

function Index() {
    const [input, setInput] = useState('');
    const inputRef = useRef<HTMLInputElement | null>(null);
    const navigate = useNavigate();

    // Automatically focus the input field on component mount
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    // Handle form submission
    const handleSubmit = (e: { preventDefault: () => void; }) => {
        e.preventDefault();
        const trimmedInput = input.trim().toLowerCase();

        const destination = PASSPHRASE_MAPPINGS[trimmedInput];
        if (destination) {
            // Navigate based on the destination type
            destination.startsWith('http') ? window.location.href = destination : navigate({ to: destination });
        } else {
            console.log('Unrecognized passphrase:', trimmedInput);
        }

        // Reset input field after submission
        setInput('');
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col items-center justify-center h-screen font-fira">
            <div className="flex items-center space-x-2 max-w-md w-full p-4 border-t border-b border-gray-300">
                <span>root@lukyfox:~$</span>
                <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Enter passphrase"
                    className="flex-grow bg-transparent focus:outline-none"
                />
            </div>
        </form>
    );
}

export const Route = createFileRoute('/')({
    component: Index
});

export default Index;
