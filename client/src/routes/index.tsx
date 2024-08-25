import { useState, useEffect, ChangeEvent, FormEvent } from 'react';
import { createFileRoute, useNavigate } from '@tanstack/react-router';

type PassphraseMappings = Record<string, string>;

const PASSPHRASE_MAPPINGS: PassphraseMappings = {
    coyoteblue: '/f2x9b0o7k',
    cananvalley: 'https://cananvalley.systems/',
};

function Index() {
    const [input, setInput] = useState<string>('');
    const [message, setMessage] = useState<string>('');
    const navigate = useNavigate();

    useEffect(() => {
        document.querySelector<HTMLInputElement>('input')?.focus();
    }, []);

    const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
        e.preventDefault();
        const destination = PASSPHRASE_MAPPINGS[input.trim().toLowerCase()];
        if (destination) {
            setMessage('Passphrase accepted. Redirecting...');
            setTimeout(() => {
                if (destination.startsWith('http')) {
                    window.location.href = destination;
                } else {
                    navigate({ to: destination, replace: true });
                }
            }, 1000);
        } else {
            setMessage('Passphrase rejected. Please try again.');
        }
        setInput('');
    };

    const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
        setInput(e.target.value);
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col items-center justify-center h-screen font-fira">
            <div className="flex items-center space-x-2 max-w-md w-full p-4 border-t border-b border-gray-300">
                <span>root@lukyfox:~$</span>
                <input
                    type="text"
                    value={input}
                    onChange={handleInputChange}
                    className="flex-grow bg-transparent border-none focus:outline-none"
                    autoFocus
                />
            </div>
            {message && (
                <p className={`mt-2 text-justify ${message.startsWith('Passphrase accepted') ? 'text-green-500' : 'text-red-500'}`}>
                    {message}
                </p>
            )}
        </form>
    );
}

export const Route = createFileRoute('/')({
    component: Index
});

export default Index;
