import { createContext, type FC, type ReactNode, use, useState } from "react";
import type { ChatItem } from "@/types/agent";

interface MultiSectionContextType {
  currentSection: ChatItem | null;
  openSection: (item: ChatItem) => void;
  closeSection: () => void;
}

const MultiSectionContext = createContext<MultiSectionContextType | null>(null);

interface MultiSectionProviderProps {
  children: ReactNode;
}

export const MultiSectionProvider: FC<MultiSectionProviderProps> = ({
  children,
}) => {
  const [currentSection, setCurrentSection] = useState<ChatItem | null>(null);

  const openSection = (item: ChatItem) => {
    setCurrentSection(item);
  };

  const closeSection = () => {
    setCurrentSection(null);
  };

  const contextValue: MultiSectionContextType = {
    currentSection,
    openSection,
    closeSection,
  };

  return (
    <MultiSectionContext.Provider value={contextValue}>
      {children}
    </MultiSectionContext.Provider>
  );
};

export const useMultiSection = (): MultiSectionContextType => {
  const context = use(MultiSectionContext);
  if (!context) {
    throw new Error(
      "useMultiSection must be used within a MultiSectionProvider",
    );
  }
  return context;
};
