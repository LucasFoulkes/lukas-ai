import { createFileRoute } from "@tanstack/react-router";
import React, { useState, useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";

function Books() {
  const [input, setInput] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [connectionStatus, setConnectionStatus] = useState<string>("");
  const [username, setUsername] = useState<string>("lukyfox");
  // Define the type for the socket reference
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    socketRef.current = io("https://192.241.134.16:8000", {
      secure: true,
      rejectUnauthorized: false, // Only for development with self-signed certificates
      transports: ['websocket', 'polling'],
      withCredentials: true
    });

    socketRef.current.on("connect", () => {
      console.log("Connected to server");
    });

    socketRef.current.on("disconnect", () => {
      console.log("Disconnected from server");
    });

    socketRef.current.on("connect_error", (error) => {
      console.error("Connection error:", error);
    });

    // Add listener for server responses
    socketRef.current.on("response", (data: { message: string }) => {
      setMessage(data.message);
      if (data.message.startsWith("SERVER: Connected as"))
        setUsername(data.message.split(" ")[3]);
    });

    // Clean up the connection when the component unmounts
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Send the input value to the server
    if (socketRef.current) {
      socketRef.current.emit("message", { data: input });
      setMessage(prevMessage => prevMessage + "\n" + `You: ${input}`);
    }
    setInput(""); // Clear the input field
  };

  return (
    <form
      className="h-screen w-screen flex flex-col justify-center items-center font-fira overflow-hidden"
      onSubmit={handleSubmit}
    >
      <div className="flex items-center border-y border-gray-300 w-full max-w-screen-md overflow-hidden p-2">
        <span>(books)root@<span className="font-medium">
          {username}
        </span>
          :~$</span>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          className="bg-transparent focus:outline-none flex-shrink w-full ml-2"
          autoFocus
        />
      </div>
      <p className="text-left w-full max-w-screen-md overflow-hidden p-2 text-sm text-blue-600">
        {message}
      </p>
    </form>
  );
}

// Route configuration
export const Route = createFileRoute("/f2x9b0o7k")({ component: Books });
export default Books;