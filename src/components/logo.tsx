import { useId } from "react";
import { cn } from "@/lib/utils";

type MarkState = "s" | "n" | "morph";

const GHOSTS = [
  { color: "var(--tide)", lag: 210, dx: -3, dy: 2 },
  { color: "var(--acid)", lag: 140, dx: 3, dy: -2 },
  { color: "var(--signal)", lag: 70, dx: 2, dy: 3 },
];

// Top and bottom bars make the S. Left and right bars make the N.
// Both letters share the diagonal, so the mark reads as either one.
function Bars() {
  return (
    <>
      <polygon points="0,0 17,0 120,103 120,120 103,120 0,17" />
      <rect className="sn-h sn-a" width="120" height="24" />
      <rect className="sn-v sn-a" width="24" height="120" />
      <rect className="sn-h sn-b" y="96" width="120" height="24" />
      <rect className="sn-v sn-b" x="96" width="24" height="120" />
    </>
  );
}

export function SNMark({
  state = "morph",
  ghosts = true,
  trip = false,
  className,
  title,
}: {
  state?: MarkState;
  ghosts?: boolean;
  trip?: boolean;
  className?: string;
  title?: string;
}) {
  const clip = useId();
  return (
    <svg
      viewBox="0 0 120 120"
      className={cn("sn-mark", className)}
      data-state={state}
      data-trip={trip}
      role={title ? "img" : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : true}
    >
      <defs>
        <clipPath id={clip}>
          <path d="M28 0H120V92a28 28 0 0 1-28 28H0V28A28 28 0 0 1 28 0Z" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clip})`}>
        {ghosts &&
          GHOSTS.map((g) => (
            <g
              key={g.color}
              className="sn-ghost"
              fill={g.color}
              style={
                {
                  "--sn-lag": g.lag,
                  "--sn-dx": g.dx,
                  "--sn-dy": g.dy,
                } as React.CSSProperties
              }
            >
              <Bars />
            </g>
          ))}
        <g fill="currentColor">
          <Bars />
        </g>
      </g>
    </svg>
  );
}

// The full logo: a fixed S next to a fixed N. Same shape, mirrored on the diagonal.
export function SNLogo({
  className,
  trip = false,
}: {
  className?: string;
  trip?: boolean;
}) {
  return (
    <span
      className={cn("inline-flex gap-[0.16em]", className)}
      role="img"
      aria-label="Synex Labs"
    >
      <SNMark state="s" trip={trip} className="h-[1em] w-[1em]" />
      <SNMark state="n" trip={trip} className="h-[1em] w-[1em]" />
    </span>
  );
}
