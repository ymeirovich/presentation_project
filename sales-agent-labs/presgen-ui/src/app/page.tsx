'use client'

import { useState } from "react"
import { TopBanner } from "@/components/TopBanner"
import { Header } from "@/components/Header"
import { SegmentedTabs } from "@/components/SegmentedTabs"
import { CoreForm } from "@/components/CoreForm"
import { DataForm } from "@/components/DataForm"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"
import { Video, Clock } from "lucide-react"
import { TabConfig } from "@/lib/types"

const TABS: TabConfig[] = [
  {
    value: "core",
    label: "PresGen Core",
  },
  {
    value: "data", 
    label: "PresGen-Data",
  },
  {
    value: "video",
    label: "PresGen-Video",
    disabled: true,
    tooltip: "Coming soon! Convert video content into slide presentations.",
  },
]

export default function Home() {
  const [activeTab, setActiveTab] = useState("core")

  const renderTabContent = () => {
    switch (activeTab) {
      case "core":
        return <CoreForm />
      case "data":
        return <DataForm />
      case "video":
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Video className="w-5 h-5" />
                PresGen-Video - Video to Slides
              </CardTitle>
              <CardDescription>
                Transform video content into professional slide presentations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
                  <Clock className="w-8 h-8 text-muted-foreground" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">Coming Soon</h3>
                  <p className="text-muted-foreground max-w-md">
                    We're working on video-to-slides conversion. Soon you'll be able to upload video content 
                    and generate professional presentations automatically.
                  </p>
                </div>
                <Button disabled variant="outline">
                  Upload Video (Coming Soon)
                </Button>
              </div>
            </CardContent>
          </Card>
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-background" suppressHydrationWarning={true}>
      <TopBanner />
      
      <Header>
        <TooltipProvider>
          <SegmentedTabs
            tabs={TABS.map(tab => ({
              ...tab,
              label: tab.disabled && tab.tooltip ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span>{tab.label}</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{tab.tooltip}</p>
                  </TooltipContent>
                </Tooltip>
              ) : tab.label
            }))}
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-auto"
          />
        </TooltipProvider>
      </Header>

      <main className="container mx-auto px-4 py-8" suppressHydrationWarning={true}>
        <div className="max-w-4xl mx-auto" suppressHydrationWarning={true}>
          {renderTabContent()}
        </div>
      </main>

      <footer className="border-t border-border bg-card/50 mt-16" suppressHydrationWarning={true}>
        <div className="container mx-auto px-4 py-6">
          <div className="text-center text-sm text-muted-foreground">
            <p>PresGen MVP - Transforming content into presentations with AI</p>
            <p className="mt-1">
              Built with Next.js, Tailwind CSS, and powered by Google AI
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
