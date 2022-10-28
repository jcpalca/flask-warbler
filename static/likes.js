"use strict";

const BASE_URL = "http://localhost:5001/api";
const $favButton = $(".fav-button");
const $favIcon = $(".fav-icon");


async function toggleLike(evt) {
  evt.preventDefault();
  console.log("This was toggled");
  const messageId = $(evt.target).closest(".like-form").data("message-id");
  const csrf_token = $favButton.data("csrf");
  console.log("This is the csrf:", csrf_token);
  console.log("This is messageId", messageId);

  axios.defaults.headers.common["X-CSRFToken"] = csrf_token;
  const resp = await axios.post(`${BASE_URL}/messages/${messageId}/like`);

  if(resp.data.favorited == true) {
    $favIcon.removeClass("bi-star").addClass("bi-star-fill text-warning");
  }
  else {
    $favIcon.removeClass("bi-star-fill text-warning").addClass("bi-star");
  }

}

$favButton.on("click", toggleLike);
