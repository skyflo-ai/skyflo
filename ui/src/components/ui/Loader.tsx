import Image from "next/image";
import React from "react";

type Props = {
  size?: number;
  logoSrc?: string;
  alt?: string;
};

export default function SphereLogoLoader({
  size = 200,
  logoSrc = "/logo_vector_transparent.png",
  alt = "Skyflo.ai",
}: Props) {
  const px = `${size}px`;
  const logo = Math.round(size * 0.45); // 45% of sphere

  return (
    <div
      className="loader-wrapper"
      role="status"
      aria-live="polite"
      aria-label="Generating"
      style={{ ["--size" as any]: px }}
    >
      <div className="sphere">
        <div className="sweep" />

        <div className="gloss" />
        <div className="vignette" aria-hidden="true" />

        <div className="logo">
          <Image
            src={logoSrc}
            alt={alt}
            width={logo}
            height={logo}
            className="logo-img"
            priority
          />
        </div>

        <div className="noise" aria-hidden="true" />
      </div>

      <span className="sr-only">Loading</span>

      <style jsx>{`
        :root {
          --sf-ink: #070b12;
          --sf-core: #0b1b2d;
          --sf-glow: #0ea5e9;
          --sf-accent: #38bdf8;
          --sf-pink: #22d3ee;
          --sf-white: #ffffff;
          --size: 180px;
        }

        .loader-wrapper {
          display: flex;
          align-items: center;
          justify-content: center;
          width: var(--size);
          height: var(--size);
          border-radius: 9999px;
          user-select: none;
          position: relative;
          isolation: isolate;
          background: transparent;
        }

        .sphere {
          position: relative;
          width: 100%;
          height: 100%;
          border-radius: 50%;
          overflow: hidden;
          background:
    /* highlight fleck — lower alpha */ radial-gradient(
              110% 110% at 30% 25%,
              rgba(255, 255, 255, 0.18) 0%,
              rgba(255, 255, 255, 0.04) 18%,
              transparent 22%
            ),
            /* main glow — lower alpha & slower falloff */
              radial-gradient(
                120% 120% at 50% 70%,
                rgba(14, 165, 233, 0.48) 0%,
                rgba(14, 165, 233, 0.32) 24%,
                var(--sf-core) 62%,
                rgba(0, 0, 0, 0.88) 100%
              );
          box-shadow: inset 0 0 60px rgba(14, 165, 233, 0.12),
            0 20px 60px rgba(56, 189, 248, 0.08);
        }

        .sweep {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          will-change: transform;
          animation: sweepRotate 2.4s linear infinite;
          pointer-events: none;
        }

        @keyframes sweepRotate {
          0% {
            transform: rotate(90deg);
            box-shadow: 0 10px 22px 0 rgba(255, 255, 255, 0.55) inset,
              0 24px 34px 0 rgba(56, 189, 248, 0.45) inset,
              0 64px 68px 0 rgba(30, 64, 175, 0.65) inset;
          }
          50% {
            transform: rotate(270deg);
            box-shadow: 0 10px 20px 0 rgba(255, 255, 255, 0.5) inset,
              0 20px 14px 0 rgba(34, 211, 238, 0.45) inset,
              0 42px 66px 0 rgba(9, 24, 54, 0.7) inset;
          }
          100% {
            transform: rotate(450deg);
            box-shadow: 0 10px 22px 0 rgba(255, 255, 255, 0.55) inset,
              0 24px 34px 0 rgba(56, 189, 248, 0.45) inset,
              0 64px 68px 0 rgba(30, 64, 175, 0.65) inset;
          }
        }

        .gloss {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          background: radial-gradient(
            65% 50% at 28% 20%,
            rgba(255, 255, 255, 0.18) 0%,
            rgba(255, 255, 255, 0.04) 40%,
            transparent 60%
          );
          mix-blend-mode: screen;
          pointer-events: none;
        }

        .vignette {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          pointer-events: none;
          mix-blend-mode: multiply;
          background: radial-gradient(
            70% 70% at 50% 50%,
            rgba(0, 0, 0, 0) 0%,
            rgba(0, 0, 0, 0.06) 55%,
            rgba(0, 0, 0, 0.14) 80%,
            rgba(0, 0, 0, 0.2) 100%
          );
          z-index: 1;
        }

        .logo {
          position: absolute;
          inset: 0;
          display: grid;
          place-items: center;
          z-index: 2;
          filter: drop-shadow(0 1px 4px rgba(255, 255, 255, 0.15));
        }

        .logo-img {
          border-radius: 12px;
        }

        .noise {
          position: absolute;
          inset: 0;
          border-radius: 50%;
          opacity: 0.12; /* was 0.24 */
          mix-blend-mode: overlay;
          pointer-events: none;
          background-size: 120px 120px;
        }

        .sr-only {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 1px, 1px);
          white-space: nowrap;
          border: 0;
        }

        @media (prefers-reduced-motion: reduce) {
          .sweep {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}
