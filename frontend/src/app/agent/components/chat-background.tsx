function ChatBackground() {
  return (
    <div className="-z-10 absolute inset-0 overflow-hidden opacity-30">
      {[
        {
          position: "left-0",
          size: "h-80 w-96",
          colors: "from-orange-200 to-orange-300",
        },
        {
          position: "left-56",
          size: "h-80 w-96",
          colors: "from-yellow-200 to-yellow-300",
        },
        {
          position: "left-96",
          size: "h-72 w-72",
          colors: "from-green-200 to-green-300",
        },
        {
          position: "right-56",
          size: "h-80 w-96",
          colors: "from-blue-200 to-blue-300",
        },
        {
          position: "right-0",
          size: "h-72 w-72",
          colors: "from-purple-200 to-purple-300",
        },
      ].map((blur, index) => (
        <div
          key={`${blur.position}-${index}`}
          className={`absolute top-1/2 ${blur.position} ${blur.size} -translate-y-1/2 transform`}
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
