import { ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

const tones = {
  solid: "bg-foreground text-background",
  signal: "bg-signal text-[#11110f]",
  ink: "bg-[#11110f] text-[#efece4]",
};
const wipes = {
  solid: "bg-signal",
  signal: "bg-foreground",
  ink: "bg-[#efece4]",
};
const hovers = {
  solid: "group-hover:text-[#11110f]",
  signal: "group-hover:text-background",
  ink: "group-hover:text-[#11110f]",
};

type CtaProps = {
  children: React.ReactNode;
  tone?: keyof typeof tones;
  size?: "md" | "lg";
  className?: string;
  href?: string;
  external?: boolean;
  type?: "button" | "submit";
  onClick?: () => void;
};

// Square button. On hover a second colour wipes in along the logo diagonal.
// Renders a link when it has an href and a button when it does not.
export function Cta({
  children,
  tone = "solid",
  size = "md",
  className,
  href,
  external = false,
  type = "button",
  onClick,
}: CtaProps) {
  const classes = cn(
    "group relative inline-flex shrink-0 items-center justify-between gap-4 overflow-hidden font-semibold",
    size === "lg" ? "h-14 px-6 text-base" : "h-11 px-4 text-sm",
    tones[tone],
    className,
  );
  const inner = (
    <>
      <span
        aria-hidden
        className={cn(
          "absolute inset-0 [clip-path:polygon(0_0,0_0,0_0)] transition-[clip-path] duration-500 ease-swift group-hover:[clip-path:polygon(0_0,220%_0,0_220%)]",
          wipes[tone],
        )}
      />
      <span className={cn("relative transition-colors duration-300", hovers[tone])}>
        {children}
      </span>
      <ArrowUpRight
        aria-hidden
        className={cn(
          "relative size-4 transition-[transform,color] duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5",
          hovers[tone],
        )}
      />
    </>
  );

  if (!href)
    return (
      <button type={type} onClick={onClick} className={classes}>
        {inner}
      </button>
    );
  return (
    <a
      href={href}
      onClick={onClick}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      className={classes}
    >
      {inner}
    </a>
  );
}

// Text link with letters that roll up into the accent colour.
export function RollLink({
  href,
  children,
  className,
  external = false,
}: {
  href: string;
  children: string;
  className?: string;
  external?: boolean;
}) {
  return (
    <a
      href={href}
      target={external ? "_blank" : undefined}
      rel={external ? "noopener noreferrer" : undefined}
      className={cn("group relative inline-block overflow-hidden", className)}
    >
      <span className="block transition-transform duration-500 ease-swift group-hover:-translate-y-full">
        {children}
      </span>
      <span
        aria-hidden
        className="absolute inset-0 translate-y-full text-signal transition-transform duration-500 ease-swift group-hover:translate-y-0"
      >
        {children}
      </span>
    </a>
  );
}
