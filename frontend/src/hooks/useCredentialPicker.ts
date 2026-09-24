import { useState, useRef, useCallback } from 'react';

export interface Credential {
  id: number;
  name: string;
  credential_type: string;
}

export function useCredentialPicker() {
  const [openPicker, setOpenPicker] = useState<string | null>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | HTMLTextAreaElement | null>>({});

  const insertCredential = useCallback((
    key: string,
    credId: number,
    currentValue: string,
    onChange: (value: string) => void
  ) => {
    const input = inputRefs.current[key];
    const placeholder = `{{cred:${credId}}}`;

    if (input) {
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? start;
      const newVal = currentValue.slice(0, start) + placeholder + currentValue.slice(end);
      onChange(newVal);
      setTimeout(() => {
        input.focus();
        input.setSelectionRange(start + placeholder.length, start + placeholder.length);
      }, 0);
    } else {
      onChange(currentValue + placeholder);
    }
    setOpenPicker(null);
  }, []);

  const registerRef = useCallback((key: string, element: HTMLInputElement | HTMLTextAreaElement | null) => {
    inputRefs.current[key] = element;
  }, []);

  const togglePicker = useCallback((key: string) => {
    setOpenPicker((prev) => (prev === key ? null : key));
  }, []);

  const closePicker = useCallback(() => {
    setOpenPicker(null);
  }, []);

  return {
    openPicker,
    togglePicker,
    closePicker,
    insertCredential,
    registerRef,
  };
}
