FROM node
WORKDIR /lib
COPY ./web/package.json ./
RUN npm install
COPY ./web .
CMD ["node","esinstall.js"]
EXPOSE 80
