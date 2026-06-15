interface AppLogoProps {
  size?: number;
  className?: string;
}

export function AppLogo({ size = 32, className = "" }: AppLogoProps) {
  return (
    <img
      src="/logo.png"
      alt="SignalSmith"
      width={size}
      height={size}
      className={`app-logo ${className}`.trim()}
      decoding="async"
    />
  );
}