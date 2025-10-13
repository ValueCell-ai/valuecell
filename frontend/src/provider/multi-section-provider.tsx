import {
  createContext,
  type FC,
  type ReactNode,
  useContext,
  useState,
} from "react";
import type { MultiSectionComponentType } from "@/types/agent";

interface SectionData {
  componentType: MultiSectionComponentType;
  data: string;
}

interface MultiSectionContextType {
  currentSection: SectionData | null;
  openSection: (componentType: MultiSectionComponentType, data: string) => void;
  closeSection: () => void;
}

const MultiSectionContext = createContext<MultiSectionContextType | null>(null);

interface MultiSectionProviderProps {
  children: ReactNode;
}

export const MultiSectionProvider: FC<MultiSectionProviderProps> = ({
  children,
}) => {
  const [currentSection, setCurrentSection] = useState<SectionData | null>(
    null,
  );

  const openSection = (
    componentType: MultiSectionComponentType,
    data: string,
  ) => {
    setCurrentSection({ componentType, data });
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
  const context = useContext(MultiSectionContext);
  if (!context) {
    throw new Error(
      "useMultiSection must be used within a MultiSectionProvider",
    );
  }
  return context;
};
