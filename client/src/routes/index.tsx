import { useState, useEffect, useRef } from 'react';
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/')({
    component: Index,
});

function Index() {
    const [input, setInput] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        console.log('Input submitted:', input);
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

export default Route;
