import { useEffect, useRef } from "react";

export default function MatrixRain({ opacity = 0.12 }: { opacity?: number }) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const chars = "アイウエオカキクケコサシスセソ0123456789ABCDEFXYZ$#@%".split("");
    let columns = 0;
    let drops: number[] = [];
    const size = 14;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      columns = Math.floor(canvas.width / size);
      drops = new Array(columns).fill(0).map(() => Math.random() * -100);
    };
    resize();
    window.addEventListener("resize", resize);

    let frame = 0;
    let raf = 0;

    const draw = () => {
      raf = requestAnimationFrame(draw);
      frame += 1;
      if (frame % 2 !== 0) return;

      ctx.fillStyle = "rgba(4, 7, 10, 0.09)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.font = `${size}px monospace`;

      for (let i = 0; i < drops.length; i += 1) {
        const char = chars[Math.floor(Math.random() * chars.length)];
        const y = drops[i] * size;
        ctx.fillStyle = Math.random() > 0.97 ? "#d7fff0" : "#00ff9c";
        ctx.fillText(char, i * size, y);
        if (y > canvas.height && Math.random() > 0.975) drops[i] = 0;
        drops[i] += 1;
      }
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{ opacity }}
    />
  );
}
