// Test script to verify file upload fix
const formData = new FormData();
const fileContent = "name,value,category\nProduct A,100,Electronics\nProduct B,200,Books\nProduct C,150,Electronics";
const file = new File([fileContent], 'test.csv', { type: 'text/csv' });

formData.append('file', file);

fetch('http://localhost:8081/data/upload', {
  method: 'POST',
  body: formData,
})
.then(response => response.json())
.then(data => {
  console.log('Upload successful:', data);
})
.catch(error => {
  console.error('Upload failed:', error);
});