import { useState, useEffect, useRef, ChangeEvent, FormEvent } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

// Type definitions
interface WebSocketMessage {
  data: string;
}

// Custom hook for managing WebSocket connection and input state
const useBooks = () => {
  const [input, setInput] = useState<string>(""); // User input state
  const [wsMessages, setWsMessages] = useState<string[]>([]); // WebSocket messages state
  const ws = useRef<WebSocket | null>(null); // WebSocket instance
  const navigate = useNavigate();

  useEffect(() => {
    // Initialize WebSocket connection
    ws.current = new WebSocket("ws://localhost:8000/ws");

    ws.current.onopen = () => console.log("WebSocket connection opened");

    ws.current.onmessage = (event: WebSocketMessage) => {
      console.log("WebSocket message received:", event.data);
      setWsMessages((prevMessages) => [...prevMessages, event.data]);
    };

    ws.current.onerror = (error: Event) =>
      console.error("WebSocket error:", error);

    ws.current.onclose = () => console.log("WebSocket connection closed");

    // Cleanup WebSocket connection on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const handleCommand = (event: FormEvent) => {
    event.preventDefault();
    const command = input.trim();

    if (command && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(command);
    }

    if (["back", "exit"].includes(command.toLowerCase())) {
      navigate({ to: "/" });
    }

    setInput(""); // Clear input field after command execution
  };

  return { wsMessages, input, setInput, handleCommand };
};

// Component for handling book commands
function Books() {
  const { wsMessages, input, setInput, handleCommand } = useBooks();

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) =>
    setInput(e.target.value);

  const message = wsMessages.slice(-1)[0] || "";

  // Determine the placeholder based on the latest message
  const placeholder =
    message === "Joined channel #ebooks" ? "search for book" : "wait a bit";

  return (
    <form
      onSubmit={handleCommand}
      className="h-screen w-screen flex flex-col justify-center items-center font-fira overflow-hidden"
    >
      <div className="flex items-center border-y border-gray-300 w-full max-w-screen-md overflow-hidden p-2">
        <span>(blue)root@lukyfox:~$</span>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          className="ml-2 bg-transparent focus:outline-none flex-shrink w-full"
          autoFocus
          placeholder={placeholder} // Set the placeholder dynamically
        />
      </div>
      <p
        className={`text-left w-full max-w-screen-md overflow-hidden p-2 text-blue-700 text-sm`}
      >
        {message && <>{message}</>}
      </p>
    </form>
  );
}

// Route configuration
export const Route = createFileRoute("/f2x9b0o7k")({ component: Books });

export default Books;
