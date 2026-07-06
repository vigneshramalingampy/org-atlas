FROM node:20-alpine

WORKDIR /app

# Copy package files first to speed up subsequent Docker builds via layer caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of your application code
COPY . .

# Inform Docker that the container listens on port 3000
EXPOSE 3000

# Next.js telemetry can be annoying in local logs; this disables it
ENV NEXT_TELEMETRY_DISABLED=1

# Fire up the Next.js development server
CMD ["npm", "run", "dev"]
