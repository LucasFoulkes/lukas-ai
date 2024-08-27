import { createFileRoute } from "@tanstack/react-router";
import React, { useState, useEffect, useRef } from "react";
import { io, Socket } from "socket.io-client";

function Books() {
  const [input, setInput] = useState<string>("");
  const [message, setMessage] = useState<string>("");

  // Define the type for the socket reference
  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // Initialize the socket connection only once
    socketRef.current = io("http://localhost:8080");

    // Handle incoming messages from the server
    socketRef.current.on("response", (data: { message: string }) => {
      setMessage(data.message);
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
    }
    setInput(""); // Clear the input field
  };

  return (
    <form
      className="h-screen w-screen flex flex-col justify-center items-center font-fira overflow-hidden"
      onSubmit={handleSubmit}
    >
      <div className="flex items-center border-y border-gray-300 w-full max-w-screen-md overflow-hidden p-2">
        <span>(books)root@lukyfox:~$</span>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          className="bg-transparent focus:outline-none flex-shrink w-full ml-2 "
          autoFocus
        />
      </div>
      <p
        className={`text-left w-full max-w-screen-md overflow-hidden p-2 text-sm text-blue-600`}
      >
        {message && <>{message}</>}
      </p>
    </form>
  );
}

// Route configuration
export const Route = createFileRoute("/f2x9b0o7k")({ component: Books });

export default Books;
