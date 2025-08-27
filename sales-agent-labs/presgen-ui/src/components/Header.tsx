import Image from "next/image"

interface HeaderProps {
  children?: React.ReactNode
}

export function Header({ children }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Image
              src="/presgen_logo.png"
              alt="PresGen"
              width={120}
              height={40}
              priority
            />
          </div>
          {children}
        </div>
      </div>
    </header>
  )
}