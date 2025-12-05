// CKEditor CDN loader for coordinator editing
(function() {
  var script = document.createElement('script');
  script.src = 'https://cdn.ckeditor.com/4.22.1/standard-all/ckeditor.js';
  script.onload = function() {
    if (window.CKEDITOR) {
      CKEDITOR.replace('full_doc_editor', {
        height: 600,
        extraPlugins: 'font,colorbutton',
        removeButtons: '',
        allowedContent: true
      });
    }
  };
  document.head.appendChild(script);
})();
