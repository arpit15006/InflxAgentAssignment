import ChatInterface from "./components/ChatInterface";

function App() {
  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center p-4 selection:bg-primary/30">
      <div className="w-full max-w-2xl mx-auto flex flex-col gap-8 items-center">
        {/* Optional top branding/intro text can go here, but keeping it clean for the SaaS feel */}
        <ChatInterface />
      </div>
    </main>
  );
}

export default App;
