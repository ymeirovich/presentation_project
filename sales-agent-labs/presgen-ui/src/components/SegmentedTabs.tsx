'use client'

import React from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"

export interface Tab {
  value: string
  label: string | React.ReactNode
  disabled?: boolean
}

interface SegmentedTabsProps {
  tabs: Tab[]
  value: string
  onValueChange: (value: string) => void
  className?: string
}

export function SegmentedTabs({ tabs, value, onValueChange, className }: SegmentedTabsProps) {
  return (
    <Tabs value={value} onValueChange={onValueChange} className={className}>
      <TabsList className="grid w-full grid-cols-3 bg-secondary">
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            disabled={tab.disabled}
            className={cn(
              "data-[state=active]:bg-primary data-[state=active]:text-primary-foreground",
              tab.disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}