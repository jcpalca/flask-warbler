"use strict";

const BASE_URL = "http://localhost:5001/api";
const $likeForm = $(".like-form");
const $favoritedButton = $(".favorite")


async function toggleLike(evt) {

  const messageId = $(evt.target).closest(".like-form").data("message-id")

  // First, send message id in request

  // get response (read if true or false)
  //toggle icon with updated class "bi-star-fill"


}

//TODO - Put event listener on button - with toggleLike() function