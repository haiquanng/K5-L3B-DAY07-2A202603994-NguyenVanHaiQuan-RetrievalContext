"use client";
import { useEffect, useRef, useState } from "react";
export function Orb() {
  const container = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let disposed = false;
    let animation: import("lottie-web").AnimationItem | undefined;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      if (media.matches) animation?.goToAndStop(18, true);
      else animation?.play();
    };
    import("lottie-web")
      .then(({ default: lottie }) => {
        if (disposed || !container.current) return;
        animation = lottie.loadAnimation({
          container: container.current,
          renderer: "svg",
          loop: true,
          autoplay: !media.matches,
          path: "/animations/animation.json",
          rendererSettings: { preserveAspectRatio: "xMidYMid meet" },
        });
        animation.addEventListener("DOMLoaded", () => {
          if (!disposed) {
            setReady(true);
            update();
          }
        });
        media.addEventListener("change", update);
      })
      .catch(() => {});
    return () => {
      disposed = true;
      animation?.destroy();
      media.removeEventListener("change", update);
    };
  }, []);
  return (
    <div className={`orb ${ready ? "orb-ready" : ""}`} aria-hidden="true">
      <div className="orb-halo" />
      <div className="orb-fallback" />
      <div className="orb-animation" ref={container} />
    </div>
  );
}
