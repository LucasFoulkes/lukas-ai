import { useState, ChangeEvent, FormEvent } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";

type PassphraseMappings = Record<string, string>;

const PASSPHRASE_MAPPINGS: PassphraseMappings = {
  coyoteblue: "/f2x9b0o7k",
  cananvalley: "https://cananvalley.systems/",
};

function Index() {
  const [input, setInput] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const navigate = useNavigate();

  const handleSubmit = (e: FormEvent<HTMLFormElement>): void => {
    e.preventDefault();
    const trimmedInput = input.trim().toLowerCase();
    const destination = PASSPHRASE_MAPPINGS[trimmedInput];

    if (destination) {
      setMessage("Passphrase accepted. Redirecting...");
      if (destination.startsWith("http")) {
        window.location.assign(destination);
      } else {
        navigate({ to: destination, replace: true });
      }
    } else {
      setMessage("Passphrase rejected. Please try again.");
    }

    setInput(""); // Reset the input field
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setInput(e.target.value);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="h-screen w-screen flex flex-col justify-center items-center font-fira overflow-hidden"
    >
      <div className="flex items-center border-y border-gray-300 w-full max-w-screen-md overflow-hidden p-2">
        <span>root@lukyfox:~$</span>
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          className="bg-transparent focus:outline-none flex-shrink w-full ml-2 "
          autoFocus
        />
      </div>
      <p
        className={`text-left ${message.startsWith("Passphrase accepted") ? "text-green-500" : "text-red-500"} w-full max-w-screen-md overflow-hidden p-2 text-sm`}
      >
        {message && <>{message}</>}
      </p>
    </form>
  );
}

export const Route = createFileRoute("/")({
  component: Index,
});

export default Index;
