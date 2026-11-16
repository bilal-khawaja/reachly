import { useState } from 'react';
import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';
import { Calendar } from '@heroui/react';
import { CalendarDate, today, getLocalTimeZone } from '@internationalized/date';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';

const toCal = (d) => (d ? new CalendarDate(d.getFullYear(), d.getMonth() + 1, d.getDate()) : null);
const toDate = (c) => new Date(c.year, c.month - 1, c.day);

export default function DatePicker({ date, onSelect, placeholder = 'Pick a date', minToday }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        render={
          <Button
            type="button"
            variant="outline"
            data-empty={!date}
            className="h-9 w-full justify-start text-left font-normal data-[empty=true]:text-muted-foreground"
          />
        }
      >
        <CalendarIcon />
        {date ? format(date, 'PPP') : <span>{placeholder}</span>}
      </PopoverTrigger>
      <PopoverContent className="w-auto p-3">
        <Calendar
          aria-label="Meeting date"
          value={toCal(date)}
          minValue={minToday ? today(getLocalTimeZone()) : undefined}
          onChange={(c) => { onSelect(c ? toDate(c) : undefined); if (c) setOpen(false); }}
        >
          <Calendar.Header>
            <Calendar.YearPickerTrigger>
              <Calendar.YearPickerTriggerHeading />
              <Calendar.YearPickerTriggerIndicator />
            </Calendar.YearPickerTrigger>
            <Calendar.NavButton slot="previous" />
            <Calendar.NavButton slot="next" />
          </Calendar.Header>
          <Calendar.Grid>
            <Calendar.GridHeader>{(day) => <Calendar.HeaderCell className="text-muted-foreground">{day}</Calendar.HeaderCell>}</Calendar.GridHeader>
            <Calendar.GridBody>{(d) => <Calendar.Cell date={d} className="data-[today=true]:font-semibold data-[today=true]:text-foreground" />}</Calendar.GridBody>
          </Calendar.Grid>
          <Calendar.YearPickerGrid>
            <Calendar.YearPickerGridBody>{({ year }) => <Calendar.YearPickerCell year={year} />}</Calendar.YearPickerGridBody>
          </Calendar.YearPickerGrid>
        </Calendar>
      </PopoverContent>
    </Popover>
  );
}
