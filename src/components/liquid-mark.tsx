"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { SNMark } from "./logo";

const VERT = `attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}`;

// Draws the SN mark as a distance field so the edges can melt and trail.
const FRAG = `
precision highp float;
uniform vec2 uRes;
uniform float uTime;
uniform vec4 uMorph;
uniform float uTrip;
uniform vec2 uMouse;
uniform vec3 uInk;
uniform vec3 uA;
uniform vec3 uB;
uniform vec3 uC;

float hash(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<3;i++){v+=a*noise(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}

float box(vec2 p,vec2 a,vec2 b){vec2 d=abs(p-(a+b)*.5)-(b-a)*.5;return max(d.x,d.y);}

float mark(vec2 p,float m){
  float t=.2;
  float hx=mix(1.,t,smoothstep(0.,.5,m));
  float vy=mix(t,1.,smoothstep(.5,1.,m));
  float d=max(abs(p.x-p.y)-.1417,box(p,vec2(0.),vec2(1.)));
  d=min(d,box(p,vec2(0.),vec2(hx,t)));
  d=min(d,box(p,vec2(0.),vec2(t,vy)));
  d=min(d,box(p,vec2(1.-hx,1.-t),vec2(1.)));
  d=min(d,box(p,vec2(1.-t,1.-vy),vec2(1.)));
  vec2 q=p;if(q.x+q.y>1.)q=1.-q;
  float r=.2333;
  if(q.x<r&&q.y<r)d=max(d,length(q-vec2(r))-r);
  return d;
}

void main(){
  vec2 uv=gl_FragCoord.xy/uRes;uv.y=1.-uv.y;
  float pad=.17;
  vec2 p=(uv-pad)/(1.-2.*pad);
  float t=uTime;
  float near=exp(-5.*dot(p-uMouse,p-uMouse));
  float amp=.016+.05*uTrip+.035*near;
  vec2 w=vec2(fbm(p*2.4+vec2(0.,t*.21)),fbm(p*2.4+vec2(5.2,-t*.18)))-.5;
  vec2 w2=vec2(fbm(p*5.+w*2.+t*.14),fbm(p*5.-w*2.-t*.11))-.5;
  vec2 pw=p+w*amp*2.+w2*amp;
  float aa=1.6/(uRes.x*(1.-2.*pad));
  float drift=.55+1.6*uTrip+1.1*near;

  vec3 col=vec3(0.);float a=0.;float m;
  m=(1.-smoothstep(-aa,aa,mark(pw+vec2(-.05,.032)*drift+w2*amp*2.2,uMorph.w)))*.95;
  col=uC*m+col*(1.-m);a=m+a*(1.-m);
  m=(1.-smoothstep(-aa,aa,mark(pw+vec2(.045,-.03)*drift-w2*amp*1.8,uMorph.z)))*.95;
  col=uB*m+col*(1.-m);a=m+a*(1.-m);
  m=(1.-smoothstep(-aa,aa,mark(pw+vec2(.026,.04)*drift+w*amp*1.6,uMorph.y)));
  col=uA*m+col*(1.-m);a=m+a*(1.-m);

  float d=mark(pw,uMorph.x);
  m=1.-smoothstep(-aa,aa,d);
  float vein=fbm(pw*3.2+w*3.+vec2(t*.09,-t*.07));
  vec3 body=mix(uInk,uA,smoothstep(.56,.8,vein)*(.25+.75*max(uTrip,near)));
  body=mix(body,uB,smoothstep(.7,.9,vein)*.6*max(uTrip,near));
  col=body*m+col*(1.-m);a=m+a*(1.-m);
  gl_FragColor=vec4(col,a);
}`;

const CYCLE = 5.6;
const LAGS = [0, 0.13, 0.26, 0.4];

function ease(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// 0 while the mark reads S, 1 while it reads N.
function morphAt(seconds: number) {
  const c = (((seconds % CYCLE) + CYCLE) % CYCLE) / CYCLE;
  if (c < 0.34) return 0;
  if (c < 0.5) return ease((c - 0.34) / 0.16);
  if (c < 0.82) return 1;
  if (c < 0.98) return 1 - ease((c - 0.82) / 0.16);
  return 0;
}

function readColor(name: string): [number, number, number] {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  const hex = raw.replace("#", "");
  if (hex.length !== 6) return [0.07, 0.07, 0.06];
  return [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255) as [
    number,
    number,
    number,
  ];
}

export function LiquidMark({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [live, setLive] = useState(false);

// Sets up the WebGL scene. Throws on any GL failure so the caller can fall
// back to the static mark. Returns a cleanup function.
function start(
  gl: WebGLRenderingContext,
  canvas: HTMLCanvasElement,
  onLive: () => void,
): () => void {
    const compile = (type: number, src: string) => {
      const shader = gl.createShader(type);
      if (!shader) throw new Error("WebGL shader creation failed");
      gl.shaderSource(shader, src);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
        throw new Error("WebGL shader compile failed");
      return shader;
    };
    const program = gl.createProgram();
    if (!program) throw new Error("WebGL program creation failed");
    gl.attachShader(program, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw new Error("WebGL program link failed");
    gl.useProgram(program);

    const buffer = gl.createBuffer();
    if (!buffer) throw new Error("WebGL buffer creation failed");
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW,
    );
    const loc = gl.getAttribLocation(program, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    const u = (name: string) => gl.getUniformLocation(program, name);
    const uRes = u("uRes");
    const uTime = u("uTime");
    const uMorph = u("uMorph");
    const uTrip = u("uTrip");
    const uMouse = u("uMouse");

    const paint = () => {
      gl.uniform3fv(u("uInk"), readColor("--foreground"));
      gl.uniform3fv(u("uA"), readColor("--signal"));
      gl.uniform3fv(u("uB"), readColor("--acid"));
      gl.uniform3fv(u("uC"), readColor("--tide"));
    };
    paint();
    const themeWatch = new MutationObserver(paint);
    themeWatch.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
      const size = Math.round(canvas.clientWidth * dpr);
      if (size === 0 || canvas.width === size) return;
      canvas.width = size;
      canvas.height = size;
      gl.viewport(0, 0, size, size);
    };
    const sizeWatch = new ResizeObserver(resize);
    sizeWatch.observe(canvas);
    resize();

    const pad = 0.17;
    const mouse = { x: 0.5, y: 0.5, tx: -2, ty: -2 };
    let trip = 0;
    let tripTarget = 0;
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      mouse.tx = (x - pad) / (1 - 2 * pad);
      mouse.ty = (y - pad) / (1 - 2 * pad);
      tripTarget = x > 0 && x < 1 && y > 0 && y < 1 ? 1 : 0;
    };
    window.addEventListener("pointermove", onMove, { passive: true });

    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let visible = true;
    const viewWatch = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
    });
    viewWatch.observe(canvas);

    let frame = 0;
    const t0 = performance.now();
    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      if (!visible || document.hidden) return;
      const t = still ? 1.2 : (now - t0) / 1000;
      mouse.x += (mouse.tx - mouse.x) * 0.08;
      mouse.y += (mouse.ty - mouse.y) * 0.08;
      trip += (tripTarget - trip) * 0.05;
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uTime, t);
      gl.uniform4f(
        uMorph,
        morphAt(t - LAGS[0]),
        morphAt(t - LAGS[1]),
        morphAt(t - LAGS[2]),
        morphAt(t - LAGS[3]),
      );
      gl.uniform1f(uTrip, still ? 0 : trip);
      gl.uniform2f(uMouse, mouse.x, mouse.y);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      if (still) cancelAnimationFrame(frame);
    };
    frame = requestAnimationFrame(draw);
    onLive();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("pointermove", onMove);
      themeWatch.disconnect();
      sizeWatch.disconnect();
      viewWatch.disconnect();
    };
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const gl = canvas.getContext("webgl", { premultipliedAlpha: true, antialias: false });
    if (!gl) return;

    // If the GPU is blocked or shaders fail, bail out: `live` stays false
    // and the static SNMark fallback underneath remains visible.
    let cleanup: (() => void) | undefined;
    try {
      cleanup = start(gl, canvas, () => setLive(true));
    } catch {
      return;
    }
    return () => cleanup?.();
  }, []);

  return (
    <div className={cn("relative aspect-square", className)} data-cursor="S or N?">
      <canvas
        ref={canvasRef}
        aria-hidden
        className={cn(
          "absolute inset-0 size-full transition-opacity duration-700",
          live ? "opacity-100" : "opacity-0",
        )}
      />
      {/* Shown until WebGL is running, and kept if it never starts. */}
      <SNMark
        title="Synex Labs logo. The letters S and N share one shape."
        className={cn(
          "absolute inset-[17%] size-[66%] transition-opacity duration-500",
          live ? "opacity-0" : "opacity-100",
        )}
      />
    </div>
  );
}
