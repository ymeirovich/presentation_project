import Image from "next/image"

interface HeaderProps {
  children?: React.ReactNode
}

export function Header({ children }: HeaderProps) {
  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col items-center space-y-4 sm:flex-row sm:justify-between sm:space-y-0">
          <div className="flex items-center space-x-4">
            <Image
              src="/presgen_logo.png"
              alt="PresGen"
              width={120}
              height={40}
              priority
            />
          </div>
          <div className="flex items-center justify-center flex-1 sm:flex-none">
            {children}
          </div>
        </div>
      </div>
    </header>
  )
}