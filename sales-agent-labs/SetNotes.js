/**
 * Set speaker notes on a slide by slide object ID.
 * @param {string} presentationId
 * @param {string} slideObjectId  // e.g., "main_slide_906df6c9"
 * @param {string} scriptText
 * @return {string} "OK" when done
 */
function setSpeakerNotes(presentationId, slideObjectId, scriptText) {
  var pres = Slides.Presentations.open(presentationId);
  // Walk slides to find the one with matching objectId
  var slides = pres.getSlides();
  for (var i = 0; i < slides.length; i++) {
    var s = slides[i];
    if (s.getObjectId() === slideObjectId) {
      var notesShape = s.getNotesPage().getSpeakerNotesShape();
      if (!notesShape) {
        // Create a notes shape if missing
        notesShape = s.getNotesPage().insertShape(SlidesApp.ShapeType.TEXT_BOX);
      }
      notesShape.getText().setText(scriptText || "");
      return "OK";
    }
  }
  throw new Error("Slide objectId not found: " + slideObjectId);
}
