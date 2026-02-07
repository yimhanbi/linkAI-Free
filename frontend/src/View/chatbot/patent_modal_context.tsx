import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import PatentDetailModal, { type PatentDetail } from "./patent_modal";

export type PatentNumberKind = "application" | "publication";

type PatentModalContextValue = {
  openPatentModal: (number: string, kind?: PatentNumberKind) => void;
};

const PatentModalContext = createContext<PatentModalContextValue | null>(null);

export function usePatentModal(): PatentModalContextValue {
  const ctx = useContext(PatentModalContext);
  if (!ctx) {
    throw new Error("usePatentModal must be used within PatentModalProvider");
  }
  return ctx;
}

type Props = {
  children: React.ReactNode;
};

export default function PatentModalProvider(props: Props) {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [selectedNumber, setSelectedNumber] = useState<string | null>(null);
  const [selectedKind, setSelectedKind] = useState<PatentNumberKind>("application");
  const [cache, setCache] = useState<Record<string, PatentDetail>>({});

  const openPatentModal = useCallback((number: string, kind: PatentNumberKind = "application") => {
    setSelectedNumber(number);
    setSelectedKind(kind);
    setIsOpen(true);
  }, []);

  const value = useMemo<PatentModalContextValue>(
    () => ({ openPatentModal }),
    [openPatentModal]
  );

  return (
    <PatentModalContext.Provider value={value}>
      {props.children}
      <PatentDetailModal
        isOpen={isOpen}
        applicationNumber={selectedNumber}
        numberKind={selectedKind}
        cache={cache}
        onCache={(appNo: string, detail: PatentDetail) => {
          setCache((prev) => ({ ...prev, [appNo]: detail }));
        }}
        onClose={() => setIsOpen(false)}
      />
    </PatentModalContext.Provider>
  );
}

