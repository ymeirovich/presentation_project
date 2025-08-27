'use client'

// import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { HelpCircle, Info } from "lucide-react"

export function TopBanner() {

  return (
    <div className="bg-primary text-primary-foreground px-4 py-2">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium">
            Welcome to PresGen MVP - Transform your content into professional presentations
          </span>
          
          <div className="flex items-center space-x-2">
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="text-primary-foreground hover:bg-primary-foreground/20">
                  <HelpCircle className="w-4 h-4 mr-1" />
                  How to Use
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>How to Use PresGen</DialogTitle>
                  <DialogDescription className="text-left">
                    Get started with creating professional presentations from your content
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 text-sm">
                  <div>
                    <h3 className="font-semibold mb-2">📝 PresGen Core (Text → Slides)</h3>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      <li>Enter your text content in the textarea or upload a document (PDF, DOCX, TXT)</li>
                      <li>Set slide count (3-15), presentation title, and template style</li>
                      <li>Choose to include AI-generated images and speaker notes</li>
                      <li>Click "Generate Slides" to create your presentation</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold mb-2">📊 PresGen-Data (Spreadsheet → Slides)</h3>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      <li>Upload a spreadsheet file (XLSX or CSV)</li>
                      <li>Select the sheet and configure data options</li>
                      <li>Add custom questions to analyze your data</li>
                      <li>Choose slide count (3-20) and chart style preferences</li>
                      <li>Generate data-driven presentations with charts and insights</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold mb-2">🎥 PresGen-Video</h3>
                    <p className="text-muted-foreground">Coming soon! Convert video content into slide presentations.</p>
                  </div>
                  
                  <div className="bg-muted p-3 rounded">
                    <h4 className="font-semibold mb-1">💡 Pro Tips</h4>
                    <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                      <li>For best results, provide clear, well-structured content</li>
                      <li>Use descriptive presentation titles for better slide organization</li>
                      <li>Speaker notes help create more detailed presentations</li>
                      <li>Data questions guide the AI to focus on specific insights</li>
                    </ul>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <Dialog>
              <DialogTrigger asChild>
                <Button variant="ghost" size="sm" className="text-primary-foreground hover:bg-primary-foreground/20">
                  <Info className="w-4 h-4 mr-1" />
                  About
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>About PresGen MVP</DialogTitle>
                  <DialogDescription className="text-left">
                    AI-powered presentation generation platform
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 text-sm">
                  <p>
                    PresGen MVP is an advanced AI presentation generator that transforms your raw content 
                    into professional, engaging slide decks automatically.
                  </p>
                  
                  <div>
                    <h3 className="font-semibold mb-2">Features</h3>
                    <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                      <li>Text-to-slides generation with multiple template styles</li>
                      <li>Spreadsheet data analysis with automatic chart generation</li>
                      <li>AI-powered image generation and speaker notes</li>
                      <li>Support for various file formats (PDF, DOCX, TXT, XLSX, CSV)</li>
                      <li>Customizable slide counts and presentation styles</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold mb-2">Technology</h3>
                    <p className="text-muted-foreground">
                      Built with advanced AI models including Google Gemini for content processing,
                      Vertex AI Imagen for image generation, and Google Slides API for presentation creation.
                    </p>
                  </div>
                  
                  <div className="text-xs text-muted-foreground pt-2 border-t">
                    PresGen MVP v1.0 - Transforming content into presentations with AI
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
        
      </div>
    </div>
  )
}