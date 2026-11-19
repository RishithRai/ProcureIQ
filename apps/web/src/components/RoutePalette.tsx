import type { LucideIcon } from "lucide-react";
import { Command as CommandIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  CommandDialog,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "./ui/command";
export default function RoutePalette({
  routes,
  open,
  onOpenChange,
}: {
  routes: { to: string; label: string; group: string; icon: LucideIcon }[];
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const navigate = useNavigate();
  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Go to workspace"
      description="Search available routes. This does not search transactions."
    >
      <CommandInput placeholder="Where would you like to go?" />
      <CommandList>
        <CommandEmpty>No matching workspace.</CommandEmpty>
        <CommandGroup heading="Navigate">
          {routes.map((r) => (
            <CommandItem
              key={r.to}
              value={`${r.label} ${r.group}`}
              onSelect={() => {
                navigate(r.to);
                onOpenChange(false);
              }}
            >
              <r.icon />
              <span>{r.label}</span>
              <CommandIcon className="ml-auto opacity-30" />
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
