import { Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxItem, ComboboxList, useComboboxAnchor } from '@/components/ui/combobox';

export function SelectCombo({ options, value, onChange, placeholder, className, defaultOpen, onOpenChange }) {
  const anchor = useComboboxAnchor();
  const selected = options.find((o) => o.value === value) ?? null;
  return (
    <Combobox key={value} items={options} value={selected} defaultOpen={defaultOpen} onOpenChange={onOpenChange} onValueChange={(o) => o && onChange(o.value)}
      itemToStringLabel={(o) => o.label} isItemEqualToValue={(a, b) => a.value === b.value}>
      <div ref={anchor}><ComboboxInput placeholder={placeholder} className={`w-full capitalize ${className ?? ''}`} /></div>
      <ComboboxContent anchor={anchor} className="w-72! min-w-72!">
        <ComboboxEmpty>No match.</ComboboxEmpty>
        <ComboboxList>
          {(o) => <ComboboxItem key={o.value} value={o} className="capitalize">{o.label}</ComboboxItem>}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}

export function SuggestCombo({ options, value, onChange, placeholder }) {
  const anchor = useComboboxAnchor();
  return (
    <Combobox items={options} value={value || null} inputValue={value}
      onInputValueChange={(v) => onChange(v ?? '')} onValueChange={(v) => onChange(v ?? '')}>
      <div ref={anchor}><ComboboxInput placeholder={placeholder} className="w-full capitalize" /></div>
      <ComboboxContent anchor={anchor} className="w-72! min-w-72!">
        <ComboboxEmpty>Press Tab to use "{value}".</ComboboxEmpty>
        <ComboboxList>
          {(o) => <ComboboxItem key={o} value={o} className="capitalize">{o}</ComboboxItem>}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  );
}
