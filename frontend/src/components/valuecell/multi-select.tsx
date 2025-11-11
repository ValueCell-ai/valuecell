import { CheckIcon, ChevronsUpDownIcon, XIcon } from "lucide-react";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "@/lib/utils";

export interface MultiSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface MultiSelectProps {
  options: MultiSelectOption[] | string[];
  value?: string[];
  defaultValue?: string[];
  onValueChange?: (value: string[]) => void;
  placeholder?: string;
  emptyText?: string;
  searchPlaceholder?: string;
  className?: string;
  disabled?: boolean;
  maxSelected?: number;
  maxDisplayed?: number;
}

export const MultiSelect = React.forwardRef<
  HTMLButtonElement,
  MultiSelectProps
>(
  (
    {
      options,
      value: controlledValue,
      defaultValue = [],
      onValueChange,
      placeholder = "Select items...",
      emptyText = "No items found.",
      searchPlaceholder = "Search...",
      className,
      disabled = false,
      maxSelected,
      maxDisplayed = 3,
    },
    ref,
  ) => {
    const [open, setOpen] = React.useState(false);
    const [internalValue, setInternalValue] =
      React.useState<string[]>(defaultValue);

    // Normalize options to MultiSelectOption[]
    const normalizedOptions = React.useMemo<MultiSelectOption[]>(() => {
      return options.map((opt) => {
        if (typeof opt === "string") {
          return { value: opt, label: opt };
        }
        return opt;
      });
    }, [options]);

    // Use controlled value if provided, otherwise use internal state
    const selectedValues = controlledValue ?? internalValue;

    const handleSelect = (optionValue: string) => {
      const isSelected = selectedValues.includes(optionValue);
      let newValue: string[];

      if (isSelected) {
        newValue = selectedValues.filter((v) => v !== optionValue);
      } else {
        // Check if max selected limit is reached
        if (maxSelected && selectedValues.length >= maxSelected) {
          return;
        }
        newValue = [...selectedValues, optionValue];
      }

      setInternalValue(newValue);
      onValueChange?.(newValue);
    };

    const handleRemove = (optionValue: string, e: React.MouseEvent) => {
      e.stopPropagation();
      const newValue = selectedValues.filter((v) => v !== optionValue);
      setInternalValue(newValue);
      onValueChange?.(newValue);
    };

    const handleClear = (e: React.MouseEvent) => {
      e.stopPropagation();
      setInternalValue([]);
      onValueChange?.([]);
    };

    const selectedOptions = normalizedOptions.filter((opt) =>
      selectedValues.includes(opt.value),
    );

    // Get displayed badges and count for remaining
    const displayedOptions = selectedOptions.slice(0, maxDisplayed);
    const remainingCount = Math.max(0, selectedOptions.length - maxDisplayed);

    const isMaxReached = maxSelected
      ? selectedValues.length >= maxSelected
      : false;

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            ref={ref}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "h-auto min-h-9 w-full justify-start gap-1 px-3 py-1.5 font-normal",
              className,
            )}
          >
            <div className="flex flex-1 items-center gap-1 overflow-hidden">
              {selectedValues.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1">
                  {displayedOptions.map((option) => (
                    <Badge
                      key={option.value}
                      variant="secondary"
                      className="h-5 gap-1 rounded-md px-1.5 py-0 font-normal text-xs"
                    >
                      <span className="max-w-[120px] truncate">
                        {option.label}
                      </span>
                      <span
                        className="cursor-pointer rounded-sm outline-none ring-offset-background transition-colors hover:bg-muted focus:ring-1 focus:ring-ring"
                        onClick={(e) => handleRemove(option.value, e)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            handleRemove(
                              option.value,
                              e as unknown as React.MouseEvent,
                            );
                          }
                        }}
                      >
                        <XIcon className="size-3 text-muted-foreground hover:text-foreground" />
                      </span>
                    </Badge>
                  ))}
                  {remainingCount > 0 && (
                    <Badge
                      variant="secondary"
                      className="h-5 rounded-md px-2 py-0 font-medium text-xs"
                    >
                      +{remainingCount}
                    </Badge>
                  )}
                </div>
              ) : (
                <span className="truncate text-muted-foreground text-sm">
                  {placeholder}
                </span>
              )}
            </div>
            <div className="ml-auto flex shrink-0 items-center gap-1 pl-2">
              {selectedValues.length > 0 && !disabled && (
                <span
                  className="cursor-pointer rounded-sm p-0.5 outline-none ring-offset-background transition-colors hover:bg-muted focus:ring-1 focus:ring-ring"
                  onClick={handleClear}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleClear(e as unknown as React.MouseEvent);
                    }
                  }}
                >
                  <XIcon className="size-3.5 text-muted-foreground hover:text-foreground" />
                </span>
              )}
              <ChevronsUpDownIcon className="size-4 shrink-0 text-muted-foreground/50" />
            </div>
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="w-(--radix-popover-trigger-width) p-0"
          align="start"
          sideOffset={4}
        >
          <Command>
            <CommandInput placeholder={searchPlaceholder} className="h-9" />
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandList className="max-h-[300px]">
              <CommandGroup onWheel={(e) => e.stopPropagation()}>
                {normalizedOptions.map((option) => {
                  const isSelected = selectedValues.includes(option.value);
                  const isDisabled =
                    option.disabled || (isMaxReached && !isSelected);

                  return (
                    <CommandItem
                      key={option.value}
                      value={option.value}
                      disabled={isDisabled}
                      onSelect={() => {
                        if (!isDisabled) {
                          handleSelect(option.value);
                        }
                      }}
                      className="cursor-pointer py-2"
                    >
                      <div
                        className={cn(
                          "mr-2 flex size-4 shrink-0 items-center justify-center rounded-[4px] border transition-colors",
                          isSelected
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-input",
                        )}
                      >
                        {isSelected && <CheckIcon className="size-4 text-xl" />}
                      </div>
                      <span
                        className={cn(
                          "flex-1 truncate text-sm",
                          isDisabled && "opacity-50",
                        )}
                      >
                        {option.label}
                      </span>
                      {isDisabled && !option.disabled && (
                        <span className="ml-2 shrink-0 text-muted-foreground text-xs">
                          (Max reached)
                        </span>
                      )}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  },
);

MultiSelect.displayName = "MultiSelect";

export default MultiSelect;
