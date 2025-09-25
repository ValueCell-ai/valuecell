function ChatBackground() {
  return (
    <div className="-z-10 absolute inset-0 overflow-hidden opacity-30">
      {[
        {
          left: "12%",
          top: "50%",
          size: "h-[40vh] w-[18vw]",
          colors: "from-yellow-200 to-yellow-300",
        },
        {
          left: "28%",
          top: "50%",
          size: "h-[38vh] w-[16vw]",
          colors: "from-green-200 to-green-300",
        },
        {
          left: "45%",
          top: "50%",
          size: "h-[42vh] w-[19vw]",
          colors: "from-teal-200 to-teal-300",
        },
        {
          left: "62%",
          top: "50%",
          size: "h-[40vh] w-[18vw]",
          colors: "from-blue-200 to-blue-300",
        },
        {
          left: "78%",
          top: "50%",
          size: "h-[35vh] w-[15vw]",
          colors: "from-purple-200 to-purple-300",
        },
      ].map((blur) => (
        <div
          key={`blur-${blur.left}-${blur.colors}`}
          className={`-translate-x-1/2 -translate-y-1/2 absolute ${blur.size}`}
          style={{ left: blur.left, top: blur.top }}
        >
          <div
            className={`h-full w-full rounded-full bg-gradient-to-br ${blur.colors} blur-[100px]`}
          />
        </div>
      ))}
    </div>
  );
}

export default ChatBackground;
