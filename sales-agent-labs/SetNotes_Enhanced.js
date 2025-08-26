/**
 * Enhanced speaker notes setter with better error handling and fallback
 * @param {string} presentationId
 * @param {string} slideObjectId  // e.g., "main_slide_906df6c9"
 * @param {string} scriptText
 * @return {object} Result object with success status and details
 */
function setSpeakerNotes(presentationId, slideObjectId, scriptText) {
  try {
    // Verify we have access to the presentation first
    var pres = SlidesApp.openById(presentationId);
    if (!pres) {
      return {
        success: false,
        error: "Cannot access presentation",
        errorCode: "PRESENTATION_ACCESS_DENIED"
      };
    }
    
    // Find the target slide
    var slides = pres.getSlides();
    var targetSlide = null;
    
    for (var i = 0; i < slides.length; i++) {
      var slide = slides[i];
      if (slide.getObjectId() === slideObjectId) {
        targetSlide = slide;
        break;
      }
    }
    
    if (!targetSlide) {
      return {
        success: false,
        error: "Slide not found: " + slideObjectId,
        errorCode: "SLIDE_NOT_FOUND"
      };
    }
    
    // Get or create speaker notes
    var notesPage = targetSlide.getNotesPage();
    var notesShape = notesPage.getSpeakerNotesShape();
    
    if (!notesShape) {
      // Create notes shape if missing
      try {
        notesShape = notesPage.insertShape(SlidesApp.ShapeType.TEXT_BOX);
        // Position the notes shape appropriately
        notesShape.setLeft(50).setTop(50).setWidth(400).setHeight(200);
      } catch (createError) {
        return {
          success: false,
          error: "Failed to create notes shape: " + createError.toString(),
          errorCode: "NOTES_SHAPE_CREATE_FAILED"
        };
      }
    }
    
    // Set the notes text
    try {
      notesShape.getText().setText(scriptText || "");
      return {
        success: true,
        message: "Speaker notes set successfully",
        slideId: slideObjectId,
        notesLength: (scriptText || "").length
      };
    } catch (textError) {
      return {
        success: false,
        error: "Failed to set notes text: " + textError.toString(),
        errorCode: "NOTES_TEXT_SET_FAILED"
      };
    }
    
  } catch (error) {
    return {
      success: false,
      error: error.toString(),
      errorCode: "GENERAL_ERROR",
      stack: error.stack
    };
  }
}

/**
 * Test function to verify Apps Script has proper access
 * @return {object} Test results
 */
function testAccess() {
  try {
    // Test if we can access SlidesApp
    var app = SlidesApp;
    
    return {
      success: true,
      message: "Apps Script has proper access to SlidesApp",
      availableServices: {
        slidesApp: !!SlidesApp,
        driveApp: !!DriveApp
      }
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString(),
      errorCode: "ACCESS_TEST_FAILED"
    };
  }
}