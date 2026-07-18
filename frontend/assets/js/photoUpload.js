// Photo upload
const photoPlaceholder = document.querySelector('.photo-placeholder');
const photoInput = document.getElementById('photoInput');

if (photoPlaceholder && photoInput) {
    photoPlaceholder.addEventListener('click', function() {
        photoInput.click();
    });

    photoInput.addEventListener('change', function(e) {
        if (e.target.files && e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = function(event) {
                document.querySelector('.photo-placeholder').style.backgroundImage = `url(${event.target.result})`;
                document.querySelector('.photo-placeholder').style.backgroundSize = 'cover';
                document.querySelector('.photo-placeholder').style.backgroundPosition = 'center';
                document.querySelector('.photo-placeholder').innerHTML = '<div class="photo-overlay">تغيير الصورة</div>';
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });
}